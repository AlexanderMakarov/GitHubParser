import os


class GitLineType(object):
    __slots__ = ('ADD', 'UNCHANGED', 'REMOVE',)

    def __init__(self):
        self.ADD = 1
        self.UNCHANGED = 0
        self.REMOVE = -1


class GitLine(object):
    __slots__ = ('type', 'line', 'features',)

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
    return next((x for x in FileType.__slots__ if getattr(FileType, x) == file_extension), FileType.UNSUPPORTED)


class GitPiece(object):
    __slots__ = ('from_line', 'from_lines', 'to_line', 'to_lines', 'parent_line', 'lines',)

    def __init__(self, from_line: int, from_lines: int, to_line: int, to_lines: int, parent_line: str, lines = []):
        self.from_line = from_line
        self.from_lines = from_lines
        self.to_line = to_line
        self.to_lines = to_lines
        self.parent_line = parent_line
        self.lines = lines


class FileType(object):
    __slots__ = ('UNSUPPORTED', 'XML', 'JAVASCRIPT', 'PYTHON', 'SWIFT', 'SH_SCRIPT', 'CONFIG',)

    def __init__(self):
        self.UNSUPPORTED = ""
        self.XML = ".xml"
        self.JAVASCRIPT = ".js"
        self.PYTHON = ".py"
        self.SWIFT = ".swift"
        self.SH_SCRIPT = ".sh"
        self.CONFIG = ".cfg"


class GitFile(object):
    __slots__ = ('file_path', 'file_name', 'file_type', 'index_line', 'pieces',)

    def __init__(self, file_path: str, index_line: str, pieces: [GitPiece]):
        self.file_path = file_path
        self.file_name = os.path.basename(file_path)
        self.file_type = parse_file_type(self.file_name)
        self.index_line = index_line
        self.pieces = pieces
