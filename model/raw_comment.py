import re
from peewee import *
from model.base_model import BaseModel


PR_NUMBER_RE = re.compile(".+pull/(\d+).+")


DeferredRawComment = DeferredRelation()


class RawComment(BaseModel):
    """
    Class of raw comment received from GitHub.
    """

    id = PrimaryKeyField()
    message = TextField()
    message_with_format = TextField()
    html_url = TextField()
    path = TextField()
    line = IntegerField()
    diff_hunk = TextField()

    class Meta:
        db_table = "raw_comments"

    """def __init__(self, message, message_with_format, html_url, path, line, diff_hunk):
        self.message = message
        self.message_with_format = message_with_format
        self.html_url = html_url
        self.path = path
        self.line = line
        self.diff_hunk = diff_hunk
        self.id = 0  # After read from db.
        self.comment = None  # After analyzing."""

    def __str__(self):
        return "RawComment '%s' at %s:%d" %(self.message, self.path, self.line)

    def parse_pr_number(self):
        match = PR_NUMBER_RE.match(self.html_url)
        return int(match.group(1))


DeferredRawComment.set_model(RawComment)