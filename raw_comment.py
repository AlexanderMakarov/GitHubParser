#!/usr/bin/env python

import re


PR_NUMBER_RE = re.compile(".+pull/(\d+).+")

class RawComment:
    """
    Class of raw comment received from GitHub.
    """

    def __init__(self, message, message_with_format, html_url, path, line, diff_hunk):
        self.message = message
        self.message_with_format = message_with_format
        self.html_url = html_url
        self.path = path
        self.line = line
        self.diff_hunk = diff_hunk

    def __str__(self):
        return "RawComment '%s' at %s:%d" %(self.message, self.path, self.line)

    def parse_pr_number(self):
        match = PR_NUMBER_RE.match(self.html_url)
        return int(match.group(1))