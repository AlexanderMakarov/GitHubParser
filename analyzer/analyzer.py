import multiprocessing.pool
from datetime import datetime
from logging import Logger

from analyzer.git_diff_parser import parse_git_diff, GitFile
from analyzer.record_parser import RecordParser
from analyzer.record_type import RecordType
from analyzer.features_keeper import Features
from model.pull_request import PullRequest
from model.raw_comment import RawComment
from analyzer.csv_worker import FileAppender
from analyzer.git.git_parser import GitRecordParser


handlers = dict()


class RecordTypeHandler:
    parser: RecordParser
    records: []

    def __init__(self, parser: RecordParser):
        self.parser = parser
        self.records = []

    def analyze(self, lines_sequence: str):
        self.records.append(self.parser.parse_git_lines(lines_sequence))
        # TODO call FileAppender


def register_record_parser(parser: RecordParser):
    handlers[parser.features_keeper.record_type] = RecordTypeHandler(parser)


def analyze_raw_comments(logger: Logger, rcs: []):
    for rc in rcs:
        rc: RawComment
        git_files = parse_git_diff(rc.diff_hunk, rc.path)
        git_files_len = len(git_files)
        if git_files_len != 1:
            logger.warning("parse_git_diff returns %d GitFile-s from %d raw comment", git_files_len, rc.id)
            continue
        git_file: GitFile = git_files[0]
        # Parse GIT features.
        records = handlers[RecordType.GIT].analyze_git_file_recursively(git_file, True)
        records_len = len(records)
        if records_len != 1:
            logger.warning("%s analyzer returns %d records for %d raw comment.", RecordType.GIT.name, records_len,
                           rc.id)
            continue
        record = records[0]
        # Add output value - rc_id.
        record[Features.RC_ID] = rc.id
        # Parse features relative to attached parsers with standard RecordParser interface.
        handler = handlers.get(git_file.file_type)
        if handler:
            records = handler.parser.analyze_git_file_recursively(git_file, True)
            records_len = len(records)
            if records_len != 1:
                logger.warning("%s analyzer returns %d records for %d raw comment.", git_file.file_type.name,
                               records_len, rc.id)
                continue
            record = records[0]
    return 1


def analyze_pull_request(pr: PullRequest):
    # Parse git data for whole pr.
    git_files = parse_git_diff(str(pr.diff), None)
    if len(git_files) > 20:  # Don't check really big pr-s.
        return []

    return parse_git_diff(str(pr.diff), None)  # TODO complete.


def analyze_pull_requests(logger: Logger, prs: []):
    records_number = 0
    for pr in prs:
        pr: PullRequest
        git_files = parse_git_diff(str(pr.diff))
        for git_file in git_files:
            git_file: GitFile
            # Parse GIT features.
            records = handlers[RecordType.GIT].analyze_git_file_recursively(git_file, False)
            records_len = len(records)

            Synchronize records received from git to othe parser.

            # Parse features relative to attached parsers with standard RecordParser interface.
            handler = handlers.get(git_file.file_type)
            if handler:
                records = handler.parser.analyze_git_file_recursively(git_file, True)
                records_len = len(records)
                if records_len != 1:
                    logger.warning("%s analyzer returns %d records for %d raw comment.", git_file.file_type.name,
                                   records_len, rc.id)
                    continue
                record = records[0]
    return records_number


def chunks_generator(items: [], chunk_size: int):
    for i in range(0, len(items), chunk_size):
        yield items[i:i + chunk_size]


def analyze_items(logger: Logger, items: [], threads_number: int):
    """
    Analyzes list of RawComment-s or PullRequest-s.
    :param logger: Logger to use.
    :param items: Items to analyze.
    :param threads_number: Number of threads to parallel analyzing on.
    :return: List of objects with features for each input item.
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
    chunk_size = chunk_size / chunk_size_divider
    estimate = items_count / threads_number * 0.005  # TODO: magic number - correct together with algorithm.
    logger.info("Start %d threads to analyze %d %ss using %d pts chunks. Wait about %.2f seconds", threads_number,
                items_count, item_name, chunk_size, estimate)
    # Split items on chunks.
    chunks = chunks_generator(items, chunk_size)
    # Prepare records parsers.
    handlers = []
    register_record_parser(GitRecordParser())
    register_record_parser(XmlRecordParser())
    register_record_parser(SwiftRecordParser())
    # Create threads poll and start analyzing.
    pool = multiprocessing.pool.ThreadPool(processes=threads_number)
    time1 = datetime.today()
    total_count: int = 0
    # Collect results.
    for i, result_item in enumerate(pool.imap_unordered(target_func, chunks, 1)):
        total_count += result_item
        completed = i + 1
        if completed % 10 == 0:  # Log status every 10 items.
            time2 = datetime.today()
            logger.info("%d/%d analyzed in %s", completed, items_count, time2 - time1)
    return total_count
