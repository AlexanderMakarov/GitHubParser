from analyzer.features_keeper import FeaturesKeeper
import numpy as np
from model.git_data import *


class RecordParser:
    features_keeper: FeaturesKeeper

    def __init__(self, features_keeper: FeaturesKeeper):
        self.features_keeper = features_keeper

    @staticmethod
    def check_binary_line(line: str):
        return "\x00" in line or any(ord(x) > 0x80 for x in line)

    def analyze_git_file_recursively(self, file: GitFile, is_diff_hunk=False):
        """
        Analyzes specified 'GitFile'.
        :param file: 'GitFile' to analyze.
        :param is_diff_hunk: Flag that we are interested only in last line in first piece in file.
        :return: 2D numpy with parsed records (one per line).
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
        return np.array(records)

    def analyze_git_file(self, file: GitFile):
        return self.features_keeper.get_row_container()

    def analyze_git_piece(self, file_level_features, piece: GitPiece):
        return np.copy(file_level_features)

    # To override.
    def analyze_git_line(self, piece_level_features, line: GitLine):
        """
        Analyzes specified 'GitLine'.
        :param piece_level_features: Numpy 1D array of already analyzed features.
        :param line: 'GitLine' to parse.
        :return: 2D numpy with parsed records (one per line).
        """
        return np.copy(piece_level_features)
