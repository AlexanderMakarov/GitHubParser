from enum import Enum
import os


class GitLineType(Enum):
    ADD = 1
    UNCHANGED = 0
    REMOVE = -1


class GitLine:
    type: GitLineType
    line: str

    def __init__(self, line: str):
        first_char = line[0:1]
        if first_char == "+":
            self.type = GitLineType.ADD
            self.line = line[1:]
        elif first_char == "-":
            self.type = GitLineType.REMOVE
            self.line = line[1:]
        else:
            self.type = GitLineType.UNCHANGED
            self.line = line


def parse_file_type(file_path: str):
    _, file_extension = os.path.splitext(file_path)
    for file_type in FileType:
        if file_extension == file_type.value:
            return file_type
    return FileType.UNSUPPORTED


class GitPiece:
    def __init__(self, from_line: int, from_lines: int, to_line: int, to_lines: int, parent_line: str,\
                lines = []):
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
