from analyzer.record_type import RecordType
from analyzer.git_dao import *
import numpy as np
from analyzer.records_producer import Features, RecordsProducer


class GitFeatures(Features):
    __slots__ = Features.__slots__ + ['GIT_LINE_TYPE', 'GIT_PIECES_NUMBER', 'GIT_LINE_LENGTH', 'V_GIT_FILE']


class GitRecordsProducer(RecordsProducer):
    def __init__(self):
        super().__init__(RecordType.GIT, GitFeatures())

    def analyze_git_file(self, file: GitFile) -> np.ndarray:
        record = self.get_row_container()
        record[self.features.GIT_PIECES_NUMBER] = len(file.pieces)
        self.add_vocabulary_feature_value(self.features.V_GIT_FILE, file.file_path, record)
        #record["git_is_%s" % file.file_type] = True  # TODO complete with lists of values
        #record["git_is_file_%s" % file.file_path] = True
        return record

    def analyze_git_piece(self, file_level_features, piece: GitPiece) -> np.ndarray:
        record = np.copy(file_level_features)
        return record

    def analyze_git_line(self, piece_level_features, line: GitLine) -> np.ndarray:
        record = np.copy(piece_level_features)
        if line.type is GitLineType.ADD:
            record[self.features.GIT_LINE_TYPE] = 1
        elif line.type is GitLineType.UNCHANGED:
            record[self.features.GIT_LINE_TYPE] = 0
        else:
            record[self.features.GIT_LINE_TYPE] = -1
        record[self.features.GIT_LINE_LENGTH] = len(line.line)
        # TODO add more features.
        return record
