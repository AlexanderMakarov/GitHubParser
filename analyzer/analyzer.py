import multiprocessing.pool
from model.comment import *
from model.raw_comment import RawComment
from logging import Logger


def analyze_raw_comment(rc: RawComment):
    hunk_lines = rc.diff_hunk.split("\n")  # TODO complete analyzer
    return Comment(raw_comment=rc, line=hunk_lines[:-1], file_type=FileType.CONFIG.value, line_type=0, git_type=0)


def analyze_raw_comments(logger: Logger, raw_comments: [RawComment], threads_number: int):
    rcs_count = len(raw_comments)
    estimate = rcs_count / threads_number * 0.0053  # TODO: magic number below - correct
    logger.info("Start %d threads to analyze %d raw comments. Wait about %d seconds", threads_number, rcs_count,
            estimate)
    pool = multiprocessing.pool.ThreadPool(processes=threads_number)
    result = pool.map(analyze_raw_comment, raw_comments, chunksize=1)
    pool.close()
    return result
