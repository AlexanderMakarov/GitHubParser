from enum import Enum
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from flask_appbuilder import Model


class FileType(Enum):
    XML = 1
    HELPER = 2
    ACTIONS = 3
    CONFIG = 4

class LineType(Enum):
    CODE = 1
    COMMENT = 2
    JAVADOC = 3
    CONSTANT = 4
    CODE_CONSTANT = 5
    CODE_COMMENT = 6
    SPLITTED = 7


class GitType(Enum):
    ADD = 1
    UNCHANGED = 0
    REMOVE = -1


class Comment(Model):
    __tablename__ = 'comments'
    id = Column(Integer, primary_key=True)
    raw_comment_id = Column(Integer)
    #raw_comment_id = Column(Integer, ForeignKey('raw_comments.id'))
    #raw_comment = relationship("RawComment", uselist=False, back_populates="comment")
    line = Column(String(), nullable=False)
    file_type = Integer()
    line_type = Integer()
