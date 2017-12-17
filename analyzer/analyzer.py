import multiprocessing.pool
from datetime import datetime, timedelta
from logging import Logger
from functools import partial

from analyzer.git_diff_parser import parse_git_diff
from analyzer.records_handler import RecordsHandler
from analyzer.records_producer import RecordsProducer
from analyzer.record_type import RecordType
from model.pull_request import PullRequest
from model.raw_comment import RawComment
from analyzer.csv_worker import FileDumper, ChunksFileDumper, save_analyzer_info, AnalyzerInfo
from analyzer.git_dao import GitFile


class Analyzer(object):
    """
    Top level class to analyze features from RawComment-s and PullRequest-s.
    Should be used in next way:
    1. Call 'analyze' method as many time as need. It will fill up 'records_XXX.csv' files by chunks.
    2. When analyzing is over call 'finalize' method. It:
        - flushes remained records into file,
        - dumps all "vocabulary features" into 'YYY_vocabulary.csv' files,
        - reads records into RAM as lines,
        - shuffles records-lines,
        - separates records to "train" and "test" parts,
        - writes records to 'XXX_train.csv' and 'XXX_test.csv' files with header rows.
    3. To analyze something else without affecting to/from previously analyzed records call 'clean_handlers' first,
        next see steps above.
    """
    __slots__ = ['logger', 'type_to_handler_dict', 'is_dump_by_chunks', 'flushed_records_number', 'positive_number']

    def __init__(self, logger: Logger, is_dump_by_chunks: bool, *args):
        self.logger = logger
        self.type_to_handler_dict = dict()
        self.is_dump_by_chunks = is_dump_by_chunks
        self.flushed_records_number = 0
        self.positive_number = 0
        for producer in args:
            producer: RecordsProducer
            record_type = producer.record_type
            if is_dump_by_chunks:
                file_dumper = ChunksFileDumper(record_type)
            else:
                file_dumper = FileDumper(record_type)
            self.type_to_handler_dict[record_type] = RecordsHandler(producer, file_dumper)

    def get_supported_types(self) -> set:
        return self.type_to_handler_dict.keys()

    def get_handler(self, type: RecordType):
        return self.type_to_handler_dict.get(type)

    def flush_handlers(self):
        for handler in self.type_to_handler_dict.values():
            handler: RecordsHandler
            self.flushed_records_number += handler.flush_records(self.logger)

    def finalize(self, train_ratio: float):
        self.flush_handlers()
        for handler in self.type_to_handler_dict.values():
            handler.finalize_records_file(self.logger, train_ratio)
        # For now count of classes = positive_number.
        info = AnalyzerInfo(self.positive_number, self.flushed_records_number, self.positive_number, train_ratio,
                            self.type_to_handler_dict.keys())
        save_analyzer_info(info)

    @staticmethod
    def chunks_generator(items: [], chunk_size: int):
        for i in range(0, len(items), chunk_size):
            yield items[i:i + chunk_size]

    def analyze_items(self, items: [], threads_number: int):
        """
        Analyzes list of RawComment-s or PullRequest-s.
        :param items: Items to analyze.
        :param threads_number: Number of threads to parallel analyzing on.
        :return: Count of analyzed records (of all types).
        """
        items_count = len(items)
        # Determine type of item.
        is_prs = False
        if isinstance(items[0], RawComment):
            target_func = analyze_raw_comments
            item_name = "raw comment"
        else:
            target_func = analyze_pull_requests
            item_name = "pull request"
            is_prs = True
        # Better to analyse items by chunks to dump them by chunks into CSV files.
        # Chunks should be small enough to get profit from multithreading
        # but big enough to don't flush them to files too often.
        chunk_size = items_count / threads_number
        # We can dump up to 100 MB chunks without RAM overload. Let's use 20000 lines (i.e. such number of records
        # could take such size).
        # It is about 20 regular PRs and 2000 regular RCs.
        chunk_size_divider = 1
        if is_prs and chunk_size > 20:
            chunk_size_divider = chunk_size / 20
        if not is_prs and chunk_size > 2000:
            chunk_size_divider = chunk_size / 20
        chunk_size = int(chunk_size / chunk_size_divider)
        self.logger.info("Start %d threads to analyze %d %ss using chunks, each %d pts.", threads_number, items_count,
                         item_name, chunk_size)
        # Split items to chunks.
        chunks = self.chunks_generator(items, chunk_size)
        # Create threads poll and start analyzing.
        pool = multiprocessing.pool.ThreadPool(processes=threads_number)
        total_count = 0
        # Collect results.
        func = partial(target_func, self)
        time1 = datetime.today()
        last_log_time = time1
        completed = 0
        for i, result_item in enumerate(pool.imap_unordered(func, chunks)):
            total_count += result_item
            completed += chunk_size
            completed = min(completed, items_count)  # Last chunk may has size less than other.
            time2 = datetime.today()
            if (time2 - last_log_time).total_seconds() >= 1:  # Log at least every second.
                total_seconds = (time2 - time1).total_seconds()
                estimate = (items_count - completed) * total_seconds / float(completed)
                estimate = timedelta(seconds=estimate)
                last_log_time = time2
                self.logger.info("%d/%d analyzed in %s. Remains about %s.", completed, items_count, time2 - time1,
                                 estimate)
        if not is_prs:
            self.positive_number += total_count
        return total_count

    def clean_handlers(self):
        for handler in self.type_to_handler_dict.values():
            handler.close()


def analyze_raw_comments(analyzer: Analyzer, rcs: []) -> int:
    """
    Analyzes raw comments. Saves data in specified handlers.
    :param analyzer: Analyzer instance to use.
    :param rcs: List of RCs to analyze.
    :return: Number of parsed records.
    """
    records_number = 0
    common_handler = analyzer.get_handler(RecordType.GIT)
    common_handler: RecordsHandler
    for rc in rcs:
        rc: RawComment
        rc_id = rc.id
        git_files = parse_git_diff(rc.diff_hunk, rc.path)
        git_files_len = len(git_files)
        if git_files_len != 1:
            analyzer.logger.warning("parse_git_diff returns %d GitFile-s from %d raw comment", git_files_len, rc_id)
            continue
        git_file: GitFile = git_files[0]
        # Parse GIT features.
        records_len = common_handler.analyze(git_file, True, rc_id)
        if records_len != 1:
            analyzer.logger.warning("%s analyzer returns %d records for %d raw comment.", RecordType.GIT.name,
                                    records_len, rc_id)
            continue
        # Parse features relative to attached parsers with standard RecordParser interface.
        handler = analyzer.get_handler(git_file.file_type)
        if handler:
            handler: RecordsHandler
            handler_records_len = handler.analyze(git_file, True, rc_id)
            if handler_records_len != 1:
                analyzer.logger.warning("%s analyzer returns %d records for %d raw comment.", git_file.file_type.name,
                                        handler_records_len, rc_id)
                continue
        records_number += 1
    if analyzer.is_dump_by_chunks:
        analyzer.flush_handlers()
    return records_number


def analyze_git_file(common_handler: RecordsHandler, handlers_dict: dict, git_file: GitFile) -> (int, RecordType):
    # Parse common features.
    records_len = common_handler.analyze(git_file, False)
    # Parse features relative to attached parsers with standard RecordParser interface.
    handler: RecordsHandler = handlers_dict.get(git_file.file_type)
    handler_records_len = 0
    if handler:
        handler_records_len = handler.analyze(git_file, False)
    return records_len + handler_records_len, git_file.file_type


def analyze_pull_requests(analyzer: Analyzer, prs: []) -> int:
    """
    Analyzes pull requests. Saves data in handlers.
    :param analyzer: Analyzer instance to use.
    :param prs: List of PRs to analyze.
    :return: Number of obtained and saved in analyzer records.
    """
    records_number = 0
    for pr in prs:
        git_files = parse_git_diff(str(pr.diff), None)
        if len(git_files) > 20:  # Don't check really big PR-s.
            continue
        type_to_handler_dict = analyzer.type_to_handler_dict
        common_handler = type_to_handler_dict.get(RecordType.GIT)
        for git_file in git_files:
            file_records_number, _ = analyze_git_file(common_handler, type_to_handler_dict, git_file)
            records_number += file_records_number
    if analyzer.is_dump_by_chunks:
        analyzer.flush_handlers()
    return records_number
