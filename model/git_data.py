from enum import Enum
import os


class GitLineType(Enum):
    ADD = 1
    UNCHANGED = 0
    REMOVE = -1


class GitLine:
    def __init__(self, line: str):
        self.line = line
        first_char = line[0:1]
        if first_char == "+":
            self.type = GitLineType.ADD
        elif first_char == "-":
            self.type = GitLineType.REMOVE
        else:
            self.type = GitLineType.UNCHANGED


def parse_file_type(file_path: str):
    for item in list():
        if item is not FileType.UNSUPPORTED:
            if file_path.endswith(item.value):
                return item


class GitPiece:
    def __init__(self, from_line: int, from_lines: int, to_line: int, to_lines: int, parent_line: str,\
                lines: [GitLine] = []):
        self.from_line = from_line
        self.from_lines = from_lines
        self.to_line = to_line
        self.to_lines = to_lines
        self.parent_line = parent_line
        self.lines = lines


class FileType(Enum):
    UNSUPPORTED = ""
    XML = ".xml"
    JAVASCRIPT = ".js"
    PYTHON = ".py"
    SWIFT = ".swift"
    SH_SCRIPT = ".sh"
    CONFIG = ".cfg"


class GitFile:
    def __init__(self, file_path: str, index_line: str, pieces: [GitPiece]):
        self.file_path = file_path
        self.file_name = os.path.basename(file_path)
        self.file_type = parse_file_type(self.file_name)
        self.index_line = index_line
        self.pieces = pieces
