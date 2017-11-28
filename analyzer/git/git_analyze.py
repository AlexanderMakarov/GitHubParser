import re
from model.git_data import GitFile, GitLine, GitPiece


DIFF_DIFF_RE = re.compile("diff --git a/(.+?)( b/)(.*)")


def parse_git_diff_diff_line(line: str):
    """
    diff --git a/iOS/actions/ui/screens/sheet.js b/iOS/actions/ui/screens/sheet.js
    """
    match = DIFF_DIFF_RE.match(line)
    if match and len(match.groups()) == 3:
        return {"a_path": match.group(1), "b_path": match.group(3)}
    return None


DIFF_POSITION_RE = re.compile("@@ -(\d+),(\d+) \+(\d+),(\d+) @@(.*)")


def parse_git_diff_position_line(line: str):
    """
    @@ -278,13 +278,15 @@ Sheet.tapRefresh = function() {
    """
    match = DIFF_POSITION_RE.match(line)
    if match and len(match.groups()) == 5:
        return GitPiece(int(match.group(1)), int(match.group(2)), int(match.group(3)), int(match.group(4)), \
                        match.group(5), [])
    return None


def parse_git_diff(diff: str, path_if_diff_hunk: str):
    """
    Parses "git diff" output into list of 'GitFile' objects.
    :param diff: String with diff lines. Can be diff_hunk or git diff.
    :param path_if_diff_hunk: If it is diff_hunk then path to file with it.
    :return: List of GitFile objects.
    """
    # git_lines_counter format:
    # 5: diff, 4: index, 3: ---, 2: +++, 1: @@ (position), 0: regular line of patch.
    lines = []
    if diff.startswith("b'"):
        diff = diff[2:-1]  # Trim "bytestring" format like [b'foo'] -> [foo]
        lines = diff.split('\\n')
        git_lines_counter = 5
    else:
        lines = diff.split('\n')
        git_lines_counter = 1
    piece: GitPiece = None
    index_line = None
    diff_data = None
    pieces = []
    files = []

    def handle_previous_piece():
        if piece and len(piece.lines) > 0:  # Use only not empty pieces.
            pieces.append(piece)

    def handle_previous_file():
        if len(pieces) > 0:
            # Create new GitFile if there is at least one piece from it.
            path = path_if_diff_hunk or diff_data['b_path']
            files.append(GitFile(path, index_line, pieces))

    for i, line in enumerate(lines):
        tmp_piece = None
        tmp_diff_data = None

        # Parse lines. Collect data into 'tmp_piece' and 'tmp_diff_data'.
        if git_lines_counter > 0:
            if git_lines_counter == 1:
                tmp_piece = parse_git_diff_position_line(line)
            elif git_lines_counter == 4:
                index_line = line
            elif git_lines_counter == 5:
                tmp_diff_data = parse_git_diff_diff_line(line)
            git_lines_counter -= 1
        else:
            # Try to parse from line "@@" string.
            tmp_piece = parse_git_diff_position_line(line)
            if tmp_piece is None:
                # Try to parse from line "diff" string.
                tmp_diff_data = parse_git_diff_diff_line(line)
                # If it is not "@@" and not "diff" then it is regular line.
                if tmp_diff_data is None and piece:
                    piece.lines.append(GitLine(line))  # Add line to piece.

        # Combine received data into 'pieces' and 'files'. Set 'tmp_piece'->'piece' and 'tmp_diff_data'->'diff_data'.
        if tmp_piece:
            handle_previous_piece()
            piece = tmp_piece
        if tmp_diff_data:  # Check started new file.
            handle_previous_piece()
            handle_previous_file()
            diff_data = tmp_diff_data
            git_lines_counter = 4  # We are here due to new file started. So "diff" is just received.
            index_line = None

    # Handle last piece and file (there is no one more "diff" line to trigger handling of it in the cycle).
    handle_previous_piece()
    handle_previous_file()
    return files
