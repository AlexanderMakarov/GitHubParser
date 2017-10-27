from enum import Enum
from peewee import *
from model.base_model import BaseModel
from model.raw_comment import DeferredRawComment  # Import of RawComment causes cross-import.


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


DeferredComment = DeferredRelation()


class Comment(BaseModel):
    id = PrimaryKeyField()
    raw_comment = ForeignKeyField(DeferredRawComment, related_name="comment", default=None)
    line = TextField()
    file_type = IntegerField()
    line_type = IntegerField()

    class Meta:
        db_table = "comments"


    """def __init__(self, raw_comment: RawComment, line: str, git_type: GitType, file_type: FileType, line_type: LineType):
        self.raw_comment = raw_comment
        self.line = line
        self.git_type = git_type
        self.file_type = file_type
        self.line_type = line_type"""


DeferredComment.set_model(Comment)