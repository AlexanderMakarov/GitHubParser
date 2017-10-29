import re
#from peewee import *
#from model.base_model import BaseModel
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from flask_appbuilder import Model


PR_NUMBER_RE = re.compile(".+pull/(\d+).+")


#DeferredRawComment = DeferredRelation()


class RawComment(Model):
    """
    Class of raw comment received from GitHub.
    """

    __tablename__ = 'raw_comments'
    id = Column(Integer, primary_key=True)
    message = Column(String(), nullable=False)
    message_with_format = Column(String(), nullable=False)
    html_url = Column(String(), nullable=False)
    path = Column(String(), nullable=False)
    line = Column(String(), nullable=False)
    diff_hunk = Column(String(), nullable=False)
    comment_id = Column(Integer, ForeignKey('comments.id'))
    #comment = relationship("Comment", uselist=False, back_populates="raw_comment")

    #class Meta:
    #    db_table = "raw_comments"

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


#DeferredRawComment.set_model(RawComment)