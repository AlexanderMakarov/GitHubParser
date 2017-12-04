from analyzer.records_producer import RecordsProducer
from analyzer.record_type import RecordType
from analyzer.git_dao import *
import numpy as np
from analyzer.features_keeper import Features, FeaturesKeeper


GitFeatures = Features.build_extension('GitFeatures', ['GIT_LINE_TYPE', 'GIT_PIECES_NUMBER', 'GIT_LINE_LENGTH'])


class GitFeaturesKeeper(FeaturesKeeper):
    def __init__(self):
        super().__init__(RecordType.GIT, GitFeatures)


class GitRecordsProducer(RecordsProducer):

    def __init__(self):
        super().__init__(GitFeaturesKeeper())

    def analyze_git_file(self, file: GitFile) -> np.ndarray:
        features = self.features_keeper.get_row_container()
        features[GitFeatures.GIT_PIECES_NUMBER.value] = len(file.pieces)
        #features["git_is_%s" % file.file_type] = True  # TODO complete with lists of values
        #features["git_is_file_%s" % file.file_path] = True
        return features

    def analyze_git_piece(self, file_level_features, piece: GitPiece) -> np.ndarray:
        features = np.copy(file_level_features)
        return features

    def analyze_git_line(self, piece_level_features, line: GitLine) -> np.ndarray:
        features = np.copy(piece_level_features)
        if line.type is GitLineType.ADD:
            features[GitFeatures.GIT_LINE_TYPE.value] = 1
        elif line.type is GitLineType.UNCHANGED:
            features[GitFeatures.GIT_LINE_TYPE.value] = 0
        else:
            features[GitFeatures.GIT_LINE_TYPE.value] = -1
        features[GitFeatures.GIT_LINE_LENGTH.value] = len(line.line)
        # TODO add more features.
        return features
