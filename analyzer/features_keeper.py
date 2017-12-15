import numpy as np
from analyzer.record_type import RecordType
from analyzer.csv_worker import dump_vocabulary
from logging import Logger


# To speed up features obtaining better to keep them in numpy arrays.
# In this case we have to know size or record and position of features in vector before start to parse them.
# 'FeaturesKeeper' is a base class for types.


class Features(object):
    __slots__ = ['RC_ID']

    def __init__(self):
        counter = 0
        for slot in self.__slots__:
            setattr(self, slot, counter)
            counter += 1


class FeaturesKeeper(object):
    """
    Class to handle features list. Should be associated with single 'Features' class.
    Provides ability to keep features for one record in Numpy array of pre-known size, build template for such record
    and set values into record array with `record[FooFeatures.BAR.value] = some` syntax.
    I.e. defining one feature takes constant time and doesn't depend from count of features.
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

    def get_row_container(self):
        """
        :return: Numpy array for one record with 0 values for all features.
        """
        return np.zeros(self.features_number, dtype=np.int16)

    def add_vocabulary_feature_value(self, feature: int, vocabulary_item: str, record: np.ndarray):
        feature_vocabulary: dict = self.vocabulary_features[feature]
        if feature_vocabulary is None:
            feature_vocabulary = dict()
            feature_vocabulary[vocabulary_item] = 0  # Index is 0 because dictionary has only one key.
            self.vocabulary_features[feature] = feature_vocabulary
            record[feature] = 0  # It is index in feature_vocabulary.
        else:
            item_index = feature_vocabulary.get(vocabulary_item)
            if item_index is None:  # No such item in vocabulary.
                item_index = len(feature_vocabulary)  # Dictionary is appended only so calculate unique index from length.
                feature_vocabulary[vocabulary_item] = item_index
            record[feature] = item_index

    def dump_vocabulary_features(self, logger: Logger):
        for feature_index, feature_vocabulary in enumerate(self.vocabulary_features):
            if feature_vocabulary is not None:
                feature_name = self.features.__slots__[feature_index]
                logger.info("  dump %s feature vocabulary with %d items", feature_name, len(feature_vocabulary))
                dump_vocabulary(feature_name, feature_vocabulary)
