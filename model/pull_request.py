from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from flask_appbuilder import Model


class PullRequest(Model):
    __tablename__ = 'pull_requests'
    id = Column(Integer, primary_key=True)
    number = Column(Integer)
    link = Column(String, nullable=False)
    state = Column(String)  # Useless to make one more structure to parse so save as string.
    diff = Column(String, nullable=False)
    raw_comments = relationship("RawComment", back_populates="pr")
