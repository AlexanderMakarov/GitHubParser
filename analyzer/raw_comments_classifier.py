import difflib
import re
from typing import Iterable
from model.raw_comment import RawComment


class RCClass:
    rcs: []
    common_message: str

    def __init__(self, common_message: str, rcs: []):
        self.rcs = rcs
        self.common_message = common_message


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


def classify_raw_comments(rcs: Iterable[RawComment]):
    rcs_to_messages = dict((rc, normalize_message_with_format(rc.message_with_format)) for rc in rcs)
    classes = []

    for i in range(0, len(rcs_to_messages)):  # "while" can cause infinite loop.
        if len(rcs_to_messages) <= 0:
            break
        same_rcs = []
        checked_message: str = None
        checked_message_rc: RawComment = None
        for rc, message in rcs_to_messages.items():
            if checked_message is None:
                checked_message = message
                checked_message_rc = rc
            elif check_normalized_messages_equal(message, checked_message):
                # Add RC with "similar" message to 'same_rcs' and remove RC from following searches.
                same_rcs.append(rc)
        same_rcs.append(checked_message_rc)
        for rc in same_rcs:
            del rcs_to_messages[rc]  # Remove all "similar" RC's, at least currently checked (unique).
        classes.append(RCClass(checked_message, same_rcs))
    return classes
