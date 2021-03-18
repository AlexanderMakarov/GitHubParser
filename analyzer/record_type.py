from enum import Enum
from analyzer.git_dao import FileType


class RecordType(Enum):
    GIT = None
    XML = FileType.XML
    SWIFT = FileType.SWIFT
