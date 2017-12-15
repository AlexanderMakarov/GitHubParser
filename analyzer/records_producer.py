from analyzer.features_keeper import FeaturesKeeper
import numpy as np
from analyzer.git_dao import *


class RecordsProducer(object):
    """
    Parses records from specified Git objects. Associated with single 'FeaturesKeeper'.
    Note: Numpy arrays ('ndarray') are faster and takes less RAM.
    """
    __slots__ = ['features_keeper']

    def __init__(self, features_keeper: FeaturesKeeper):
        self.features_keeper = features_keeper

    @staticmethod
    def check_binary_line(line: str):
        return "\x00" in line or any(ord(x) > 0x80 for x in line)

    def analyze_git_file_recursively(self, file: GitFile, is_diff_hunk=False) -> list:
        """
        Analyzes specified 'GitFile'. Returns list of numpy arrays-records.
        Don't use 2D numpy array because need to append and extend list of records.
        :param file: 'GitFile' to analyze.
        :param is_diff_hunk: Flag that we are interested only in last line in first piece in file.
        :return: List of numpy arrays with parsed records.
        """
        records = []
        file_level_features = self.analyze_git_file(file)
        for piece in file.pieces:
            piece_level_features = self.analyze_git_piece(file_level_features, piece)
            # Set what to handle.
            lines = piece.lines
            if is_diff_hunk:
                lines = lines[-1:]
            # Handle chosen lines.
            is_first_line = True
            for line in lines:
                if is_first_line:
                    is_first_line = False
                    if self.check_binary_line(line.line) is None:
                        break  # Don't check binary files.
                line_level_features = self.analyze_git_line(piece_level_features, line)
                records.append(line_level_features)  # Save features.
        return records

    # To override.
    def analyze_git_file(self, file: GitFile) -> np.ndarray:
        return self.features_keeper.get_row_container()

    # To override.
    def analyze_git_piece(self, file_level_features, piece: GitPiece) -> np.ndarray:
        return np.copy(file_level_features)

    # To override.
    def analyze_git_line(self, piece_level_features, line: GitLine) -> np.ndarray:
        """
        Analyzes specified 'GitLine'.
        :param piece_level_features: Numpy 1D array of already analyzed features.
        :param line: 'GitLine' to parse.
        :return: 2D numpy with parsed records (one per line).
        """
        return np.copy(piece_level_features)
