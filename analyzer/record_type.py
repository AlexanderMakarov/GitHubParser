from enum import Enum
from model.git_data import FileType


class RecordType(Enum):
    GIT = None
    XML = FileType.XML
    SWIFT = FileType.SWIFT
