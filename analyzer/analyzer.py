import multiprocessing.pool
from datetime import datetime, timedelta
from logging import Logger
from functools import partial

from analyzer.git_diff_parser import parse_git_diff
from analyzer.records_producer import RecordsProducer
from analyzer.record_type import RecordType
from analyzer.features_keeper import Features
from model.pull_request import PullRequest
from model.raw_comment import RawComment
from analyzer.csv_worker import FileAppender, dump_records
from analyzer.git_dao import GitFile
import sys


class RecordHandler(object):
    """
    Keep records during analyzing and dump records to file(s). Works with records only one type.
    For one session of analyzing need to create and use few handlers - one per each record type.
    """
    __slots__ = ['record_type', 'producer', 'file_appender', '_records', 'flushed_records_number']

    def __init__(self, producer: RecordsProducer):
        self.record_type = producer.features_keeper.record_type
        self.producer = producer
        self.file_appender = FileAppender(self.record_type)
        self._records = []
        self.flushed_records_number = 0

    def analyze(self, git_file: GitFile, is_diff_hunk, rc_id: int = -1):
        """
        Analyzes specified 'GitFile' and saves resulting records into inner 'records'.
        :param git_file: 'GitFile' to analyze.
        :param is_diff_hunk: Flag that 'GitFile' contains "diff_hunk" instead of usual diff.
        :param rc_id: RawComment ID if exist.
        :return: Count of records produced from specified git file.
        """
        records = self.producer.analyze_git_file_recursively(git_file, is_diff_hunk)
        if rc_id > 0:
            for record in records:
                record[self.producer.features_keeper.features.RC_ID] = rc_id
        self._records.extend(records)  # Support case when 'analyze' called few times before 'clean_records' call.
        return len(records)

    def clean_records(self):
        self._records = []

    def flush_records(self):
        records_len = len(self._records)
        if records_len >= 0:
            self.file_appender.flush_records(self._records)
            self.clean_records()
            self.flushed_records_number += records_len

    def finalize_records_file(self, logger: Logger):
        logger.info("  %d bytes for %d records list with %d features each", sys.getsizeof(self._records),
                    len(self._records), len(self._records[0]))
        # self.flush_records(logger)
        # self.file_appender.write_head(self.flushed_records_number, self.producer.features_keeper.get_feature_names())
        dump_records(self.record_type, self.producer.features_keeper.get_feature_names(), self._records)
        self.clean_records()
        self.producer.features_keeper.dump_vocabulary_features(logger)


class Analyzer:
    """
    Class to parse/analyze features from RawComment-s and PullRequest-s.
    Should be used in next way:
    1. Call 'analyze' method as many time as need. It will fill up 'records_XXX.csv' files by chunks.
    2. When analyzing is over call 'finalize' method. It will preappend 'records_XXX.csv' files with header rows
        and dump all "vocabulary features" into 'YYY_vocabulary.csv' files.
    """
    logger: Logger
    type_to_handler_dict: dict

    def __init__(self, logger: Logger, *args):
        self.logger = logger
        self.type_to_handler_dict = dict()
        for producer in args:
            self.type_to_handler_dict[producer.features_keeper.record_type] = RecordHandler(producer)

    def get_handler(self, type: RecordType):
        return self.type_to_handler_dict.get(type)

    def clean_handlers(self):
        for handler in self.type_to_handler_dict.values():
            handler.clean_records()

    def flush_handlers(self):
        for handler in self.type_to_handler_dict.values():
            handler.flush_records()

    def finalize(self, logger: Logger):
        for handler in self.type_to_handler_dict.values():
            handler.finalize_records_file(logger)

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
        total_count: int = 0
        # Collect results.
        func = partial(target_func, self)
        time1 = datetime.today()
        last_log_time = time1
        completed = 0
        for i, result_item in enumerate(pool.imap_unordered(func, chunks)):
            total_count += result_item
            completed += chunk_size
            time2 = datetime.today()
            if (time2 - last_log_time).total_seconds() >= 1:  # Log at least every second.
                total_seconds = (time2 - time1).total_seconds()
                estimate = (items_count - completed) * total_seconds / float(completed)
                estimate = timedelta(seconds=estimate)
                last_log_time = time2
                self.logger.info("%d/%d analyzed in %s. Remains about %s.", completed, items_count, time2 - time1,
                                 estimate)
        time2 = datetime.today()
        self.logger.info("Total %d records get after %d %ss analyzing. Take %s.", total_count, items_count, item_name,
                         time2 - time1)
        return total_count


def analyze_raw_comments(analyzer: Analyzer, rcs: []) -> int:
    """
    Analyzes raw comments. Saves data in specified handlers.
    :param analyzer: Analyzer instance to use.
    :param rcs: List of RCs to analyze.
    :return: Number of parsed records.
    """
    records_number = 0
    common_handler = analyzer.type_to_handler_dict.get(RecordType.GIT)
    common_handler: RecordHandler
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
        handler = analyzer.type_to_handler_dict.get(git_file.file_type)
        if handler:
            handler: RecordHandler
            handler_records_len = len(handler.analyze(git_file, True, rc_id))
            if handler_records_len != 1:
                analyzer.logger.warning("%s analyzer returns %d records for %d raw comment.", git_file.file_type.name,
                                        handler_records_len, rc_id)
                continue
        records_number += 1
    return records_number


def analyze_pull_requests(analyzer: Analyzer, prs: []) -> int:
    """
    Analyzes pull requests. Saves data in handlers.
    :param analyzer: Analyzer instance to use.
    :param prs: List of PRs to analyze.
    :return: Number of parsed records.
    """
    records_number = 0
    common_handler: RecordHandler = analyzer.type_to_handler_dict.get(RecordType.GIT)
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
            handler = analyzer.type_to_handler_dict.get(git_file.file_type)
            if handler:
                handler: RecordHandler
                records_len = handler.analyze(git_file, False)
            records_number += records_len
    return records_number
