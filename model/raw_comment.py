import re
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from flask_appbuilder import Model


PR_NUMBER_RE = re.compile(".+pull/(\d+).+")


class RawComment(Model):
    """
    Class of raw comment received from GitHub.
    """

    __tablename__ = 'raw_comments'
    id = Column(Integer, primary_key=True)
    message = Column(String, nullable=False)
    message_with_format = Column(String(), nullable=False)
    html_url = Column(String, nullable=False, unique=True)  # TODO satisfy on "save"!!!
    path = Column(String, nullable=False)
    line = Column(String, nullable=False)
    diff_hunk = Column(String, nullable=False)
    updated_at = Column(String, nullable=False)
    # One PullRequest can contain few RawComment-s.
    pr_id = Column(Integer, ForeignKey("pull_requests.id"))
    pr = relationship("PullRequest", back_populates="raw_comments")

    def parse_pr_number(self):
        match = PR_NUMBER_RE.match(self.html_url)
        return int(match.group(1))
