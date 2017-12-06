from analyzer.records_producer import RecordsProducer
from analyzer.record_type import RecordType
from analyzer.git_dao import *
import numpy as np
from analyzer.features_keeper import Features, FeaturesKeeper


GitFeatures = Features.build_extension('GitFeatures',
                                       ['GIT_LINE_TYPE', 'GIT_PIECES_NUMBER', 'GIT_LINE_LENGTH', 'GIT_FILE'])


class GitFeaturesKeeper(FeaturesKeeper):
    def __init__(self):
        super().__init__(RecordType.GIT, GitFeatures)


class GitRecordsProducer(RecordsProducer):

    def __init__(self):
        super().__init__(GitFeaturesKeeper())

    def analyze_git_file(self, file: GitFile) -> np.ndarray:
        record = self.features_keeper.get_row_container()
        record[GitFeatures.GIT_PIECES_NUMBER.value] = len(file.pieces)
        self.features_keeper.add_vocabulary_feature_value(GitFeatures.GIT_FILE, file.file_path, record)
        #record["git_is_%s" % file.file_type] = True  # TODO complete with lists of values
        #record["git_is_file_%s" % file.file_path] = True
        return record

    def analyze_git_piece(self, file_level_features, piece: GitPiece) -> np.ndarray:
        record = np.copy(file_level_features)
        return record

    def analyze_git_line(self, piece_level_features, line: GitLine) -> np.ndarray:
        record = np.copy(piece_level_features)
        if line.type is GitLineType.ADD:
            record[GitFeatures.GIT_LINE_TYPE.value] = 1
        elif line.type is GitLineType.UNCHANGED:
            record[GitFeatures.GIT_LINE_TYPE.value] = 0
        else:
            record[GitFeatures.GIT_LINE_TYPE.value] = -1
        record[GitFeatures.GIT_LINE_LENGTH.value] = len(line.line)
        # TODO add more features.
        return record
