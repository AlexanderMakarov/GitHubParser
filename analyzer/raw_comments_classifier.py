import difflib
import re
from typing import Iterable
from model.raw_comment import RawComment
from analyzer.csv_worker import dump_rcclasses
from logging import Logger
from collections import OrderedDict
from operator import itemgetter
from datetime import datetime
from itertools import groupby


class RCClass:
    raw_comments: []
    common_message: str

    def __init__(self, common_message: str, rcs: []):
        self.raw_comments = rcs
        self.common_message = common_message

    def serialize_raw_comments(self):
        return " ".join(str(x) for x in self.raw_comments)


REMOVE_CODE_RE = re.compile("`.+`")


def normalise_message_line(line: str):
    return REMOVE_CODE_RE.sub("", line)


def normalize_message_with_format(message_with_format: str):
    lines = message_with_format.split("\n")
    result_lines = []
    is_code = False
    for line in lines:
        if not is_code:
            if line == "```":
                is_code = True
            if not line.startswith(">"):  # Handle only not quotes.
                result_lines.append(normalise_message_line(line))
        elif line == "```":
            is_code = False
    return "".join(result_lines)


def check_normalized_messages_equal(a: str, b: str):
    ratio = difflib.SequenceMatcher(None, a, b).ratio()
    return ratio > 0.9  # Float number - comparison threshold.


def extract_raw_comments_data(rcs: []):
    rcs_to_messages = []
    for rc in rcs:
        rc: RawComment
        rcs_to_messages.append([rc.id, rc.message_with_format])
    return rcs_to_messages


def classify_raw_comments(logger: Logger, rcs: []):
    rcs_to_messages = extract_raw_comments_data(rcs)
    # Sort to speed up.
    #rcs_to_messages = OrderedDict(sorted(rcs_to_messages.items(), key=itemgetter(1)))
    classes = []
    rcs_number = len(rcs_to_messages)
    estimate = rcs_number * 10  # Value - found experimentally.
    logger.info("Start analyse %d raw commits. Wait %d seconds.", rcs_number, estimate)
    for i in range(0, rcs_number):  # "while" can cause infinite loop.
        if len(rcs_to_messages) <= 0:
            break
        same_rcs = []
        checked_message: str = None
        checked_message_rc = 0
        tmp_list = []
        for pair in rcs_to_messages:
            rc_id = pair[0]
            message = pair[1]
            if checked_message is None:
                checked_message = message
                checked_message_rc = rc_id
            else:
                if check_normalized_messages_equal(message, checked_message):
                    # Add RC with "similar" message to 'same_rcs' and remove RC from following searches.
                    same_rcs.append(rc_id)
                else:
                    tmp_list.append(pair)  # Append to tmp "new" list if not matched.
        same_rcs.append(checked_message_rc)
        classes.append(RCClass(checked_message, same_rcs))
        rcs_to_messages = tmp_list  # Change iterated list to shrinked.
    return classes


def classify_raw_comments_hash(logger: Logger, rcs: []):
    rcs_to_messages = extract_raw_comments_data(rcs)
    rcs_to_messages = sorted(rcs_to_messages, key=lambda x: x[1])  # Sort by messages.
    classes = []
    for key, group in groupby(rcs_to_messages, lambda item: item[1]):
        classes.append(RCClass(key, list(group)))
    return classes


def classify_and_dump_raw_comments(logger: Logger, rcs: []):
    #classes = classify_raw_comments(logger, rcs)  # 200 rcs - 11 sec
    classes = classify_raw_comments_hash(logger, rcs)  # 500 rcs - 9 sec
    logger.info("Found %d classes in %d raw comments", len(classes), len(rcs))
    path = dump_rcclasses(classes)
    logger.info("Dump raw comments %d classes into %s", len(classes), path)
    return path
