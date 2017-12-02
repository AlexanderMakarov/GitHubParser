import multiprocessing.pool
from datetime import datetime
from logging import Logger
from functools import partial

from analyzer.git_diff_parser import parse_git_diff
from analyzer.records_producer import RecordsProducer
from analyzer.record_type import RecordType
from analyzer.features_keeper import Features
from model.pull_request import PullRequest
from model.raw_comment import RawComment
from analyzer.csv_worker import FileAppender
from analyzer.git.git_producer import GitRecordsProducer
from analyzer.git_dao import GitFile


class RecordTypeHandler:
    record_type: RecordType
    producer: RecordsProducer
    records: list

    def __init__(self, producer: RecordsProducer):
        self.record_type = producer.features_keeper.record_type
        self.producer = producer
        self.file_appender = FileAppender(self.record_type)
        self.clean_records()

    def analyze(self, git_file: GitFile, is_diff_hunk):
        """
        Analyzes specified 'GitFile' and saves resulting records into inner 'records'.
        :param git_file: 'GitFile' to analyze.
        :param is_diff_hunk: Flag that 'GitFile' contains "diff_hunk" instead of usual diff.
        :return: Count of records produced from specified git file.
        """
        # 'records' below is Numpy 1D array.
        records = self.producer.analyze_git_file_recursively(git_file, is_diff_hunk)
        self.records.extend(records)  # Support case when 'analyze' called few times before 'clean_records' call.
        return len(records)

    def clean_records(self):
        self.records = []

    def flush_records(self):
        if len(self.records) > 0:
            self.file_appender.write_records(self.records)
            self.clean_records()

    def close(self):
        self.file_appender.write_head(self.producer.features_keeper.get_feature_names())


class Analyzer:
    type_to_handler: dict

    def __init__(self, *args):
        self.type_to_handler = dict()
        for producer in args:
            self.type_to_handler[producer.features_keeper.record_type] = RecordTypeHandler(producer)

    def get_handler(self, type: RecordType):
        return self.type_to_handler.get(type)

    def clean_handlers(self):
        for handler in self.type_to_handler.values():
            handler.clean_records()

    def flush_handlers(self):
        for handler in self.type_to_handler.values():
            handler.flush_records()

    def close_handlers(self):
        for handler in self.type_to_handler.values():
            handler.close()

    @staticmethod
    def chunks_generator(items: [], chunk_size: int):
        for i in range(0, len(items), chunk_size):
            yield items[i:i + chunk_size]

    def analyze_items(self, logger: Logger, items: [], threads_number: int):
        """
        Analyzes list of RawComment-s or PullRequest-s.
        :param logger: Logger to use.
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
        # We can dump up to 100 MB chunks without RAM overload. Let's use 20000 lines.
        # We can parse about 10 lines from rc item and about 1000 lines from pr item.
        chunk_size_divider = 1
        if is_prs and chunk_size > 20:
            chunk_size_divider = chunk_size / 20
        if not is_prs and chunk_size > 2000:
            chunk_size_divider = chunk_size / 20
        chunk_size = int(chunk_size / chunk_size_divider)
        estimate = items_count / threads_number * 0.005  # TODO: magic number - correct together with algorithm.
        logger.info("Start %d threads to analyze %d %ss using %d pts chunks. Wait about %.2f seconds", threads_number,
                    items_count, item_name, chunk_size, estimate)
        # Split items on chunks.
        chunks = self.chunks_generator(items, chunk_size)
        # Create threads poll and start analyzing.
        pool = multiprocessing.pool.ThreadPool(processes=threads_number)
        time1 = datetime.today()
        total_count: int = 0
        # Collect results.
        func = partial(target_func, logger, self)
        last_log_time = time1
        for i, result_item in enumerate(pool.imap_unordered(func, chunks)):
            total_count += result_item
            completed = i + 1
            time2 = datetime.today()
            if (time2 - last_log_time).total_seconds() >= 1:  # Log at least every second.
                last_log_time = time2
                logger.info("%d/%d analyzed in %s", completed, items_count, time2 - time1)
        time2 = datetime.today()
        logger.info("Total %d records obtained in %s.", total_count, time2 - time1)
        return total_count


def analyze_raw_comments(logger: Logger, analyzer: Analyzer, rcs: []) -> int:
    analyzer.clean_handlers()
    common_handler = analyzer.get_handler(RecordType.GIT)
    common_handler: RecordTypeHandler
    for rc in rcs:
        rc: RawComment
        git_files = parse_git_diff(rc.diff_hunk, rc.path)
        git_files_len = len(git_files)
        if git_files_len != 1:
            logger.warning("parse_git_diff returns %d GitFile-s from %d raw comment", git_files_len, rc.id)
            continue
        git_file: GitFile = git_files[0]
        # Parse GIT features.
        records_len = common_handler.analyze(git_file, True)
        if records_len != 1:
            logger.warning("%s analyzer returns %d records for %d raw comment.", RecordType.GIT.name, records_len,
                           rc.id)
            continue
        # Add output value - rc_id.
        common_handler.records[0][Features.RC_ID.value] = rc.id
        # Parse features relative to attached parsers with standard RecordParser interface.
        handler = analyzer.get_handler(git_file.file_type)
        if handler:
            handler: RecordTypeHandler
            records_len = handler.analyze(git_file, True)
            handler_records_len = len(handler.records)
            if handler_records_len != 1:
                logger.warning("%s analyzer returns %d records for %d raw comment.", git_file.file_type.name,
                               handler_records_len, rc.id)
                continue
    analyzer.flush_handlers()
    return 1


def analyze_pull_requests(logger: Logger, analyzer: Analyzer, prs: []) -> int:
    analyzer.clean_handlers()
    records_number = 0
    common_handler = analyzer.get_handler(RecordType.GIT)
    common_handler: RecordTypeHandler
    for pr in prs:
        pr: PullRequest
        git_files = parse_git_diff(str(pr.diff), None)
        if len(git_files) > 20:  # Don't check really big pr-s.
            continue
        for git_file in git_files:
            git_file: GitFile
            # Parse common features.
            records_len = common_handler.analyze(git_file, False)
            # Parse features relative to attached parsers with standard RecordParser interface.
            handler = analyzer.get_handler(git_file.file_type)
            if handler:
                handler: RecordTypeHandler
                records_len = handler.analyze(git_file, False)
            records_number += records_len
    analyzer.flush_handlers()
    return records_number
