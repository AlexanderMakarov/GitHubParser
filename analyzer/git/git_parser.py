from analyzer.git.git_features import GitFeatures, GitFeaturesKeeper
from analyzer.record_parser import RecordParser
from model.git_data import *
import numpy as np


class GitRecordParser(RecordParser, GitFeaturesKeeper):

    def analyze_git_file(self, file: GitFile):
        features = self.features_keeper.get_row_container()
        #file_level_features["git_is_%s" % file.file_type] = True  # TODO complete with lists of values
        #file_level_features["git_is_file_%s" % file.file_path] = True
        return features

    def analyze_git_piece(self, file_level_features, piece: GitPiece):
        features = np.copy(file_level_features)
        features[GitFeatures.GIT_PIECES_NUMBER]
        return features

    def analyze_git_line(self, piece_level_features, line: GitLine):
        features = np.copy(piece_level_features)
        if line.type is GitLineType.ADD:
            features[GitFeatures.GIT_LINE_TYPE] = 1
        elif line.type is GitLineType.UNCHANGED:
            features[GitFeatures.GIT_LINE_TYPE] = 0
        else:
            features[GitFeatures.GIT_LINE_TYPE] = -1
            features[GitFeatures.GIT_LINE_LENGTH] = len(line)
        # TODO add more features.
        return features
