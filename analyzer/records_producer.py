import numpy as np
from analyzer.record_type import RecordType
from analyzer.git_dao import *


# To speed up features obtaining better to keep them in numpy arrays.
# In this case we have to know size or record and position of features in vector before start to parse them.


class Features(object):
    __slots__ = ['RC_ID']

    def __init__(self):
        counter = 0
        for slot in self.__slots__:
            setattr(self, slot, counter)
            counter += 1


class RecordsProducer(object):
    """
    Base class to parse features of single record type from git DAO into one or few records.
    Provides ability to keep features for one record in Numpy array of pre-known size, build template for such record
    and set values into record array with `record[self.features.FOO] = bar` syntax.
    Defining one feature takes constant time and doesn't depend from count of features.
    Also it handles list-based features. See `add_vocabulary_feature_value` method.
    """
    __slots__ = ['record_type', 'features', 'features_number', 'vocabulary_features']

    def __init__(self, record_type: RecordType, features: Features):
        self.record_type = record_type
        self.features = features
        self.features_number = len(self.features.__slots__)
        self.vocabulary_features = np.empty(self.features_number, dtype=object)
        self.vocabulary_features.fill(None)

    def get_feature_names(self) -> list:
        return [k for k in self.features.__slots__]

    def get_row_container(self) -> np.ndarray:
        """
        :return: Numpy array for one record with 0 values for all features.
        """
        return np.zeros(self.features_number, dtype=np.int16)

    def add_vocabulary_feature_value(self, feature: int, vocabulary_item: str, record: np.ndarray):
        """
        Adds into inner 'vocabulary_features' numpy 2D array vocabulary feature.
        :param feature: Feature index.
        :param vocabulary_item: Value from vocabulary.
        :param record: Record to set feature value into.
        """
        feature_vocabulary: dict = self.vocabulary_features[feature]
        if feature_vocabulary is None:
            feature_vocabulary = dict()
            feature_vocabulary[vocabulary_item] = 0  # Index is 0 because dictionary has only one key.
            self.vocabulary_features[feature] = feature_vocabulary
            record[feature] = 0  # It is index in feature_vocabulary.
        else:
            item_index = feature_vocabulary.get(vocabulary_item)
            if item_index is None:  # No such item in vocabulary.
                item_index = len(feature_vocabulary)  # Dictionary is appended only so unique index = length.
                feature_vocabulary[vocabulary_item] = item_index
            record[feature] = item_index

    @staticmethod
    def check_binary_line(line: str) -> bool:
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
        """
        Analyzes specified 'GitFile'.
        :param file: 'GitFile' to parse.
        :return: 1D numpy array with parsed record.
        """
        return self.features_keeper.get_row_container()

    # To override.
    def analyze_git_piece(self, file_level_features, piece: GitPiece) -> np.ndarray:
        """
        Analyzes specified 'GitPiece'.
        :param file_level_features: Numpy 1D array of already analyzed features.
        :param piece: 'GitPiece' to parse.
        :return: 1D numpy array with parsed record.
        """
        return np.copy(file_level_features)

    # To override.
    def analyze_git_line(self, piece_level_features, line: GitLine) -> np.ndarray:
        """
        Analyzes specified 'GitLine'.
        :param piece_level_features: Numpy 1D array of already analyzed features.
        :param line: 'GitLine' to parse.
        :return: 1D numpy array with parsed record.
        """
        return np.copy(piece_level_features)
