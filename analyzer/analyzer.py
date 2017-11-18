import multiprocessing.pool
from model.raw_comment import RawComment
from model.pull_request import PullRequest
from logging import Logger
from analyzer.git_analyze import parse_git_diff
from multiprocessing import Process
from datetime import datetime


def analyze_raw_comment(rc: RawComment):
    return parse_git_diff(rc.diff_hunk, rc.path)  # TODO complete.


def analyze_pull_request(pr: PullRequest):
    return parse_git_diff(pr.diff, None)  # TODO complete.


def analyze_items(logger: Logger, items: [], threads_number: int):
    """
    Analyzes list of RawComment-s or PullRequest-s.
    :param logger: Logger to use.
    :param items: Items to analyze.
    :param threads_number: Number of threads to parallel analyzing on.
    :return: List of objects with features for each input item.
            1 object per RawComment and 1 objects per line in PullRequest.
    """
    items_count = len(items)
    result = []
    # Determine type of item.
    if isinstance(items[0], RawComment):
        target_func = analyze_raw_comment
        item_name = "raw comment"
    else:
        target_func = analyze_pull_request
        item_name = "pull request"
    estimate = items_count / threads_number * 0.005  # TODO: magic number below - correct together with algorithm.
    logger.info("Start %d threads to analyze %d %ss. Wait about %.2f seconds", threads_number, items_count, item_name,
            estimate)
    # Create threads poll and start analyzing.
    pool = multiprocessing.pool.ThreadPool(processes=threads_number)
    time1 = datetime.today()
    for i, result_item in enumerate(pool.imap_unordered(target_func, items, 1)):
        result.extend(result_item)  # TODO result_item is a list of 'GitFile'-s for now. - complete.
        completed = i + 1
        if completed % 10 == 0:  # Log status every 10 items.
            time2 = datetime.today()
            logger.info("%d/%d analyzed in %s", completed, items_count, time2 - time1)
    return result
