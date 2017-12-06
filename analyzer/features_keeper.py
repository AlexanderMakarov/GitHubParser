from enum import Enum, auto
import numpy as np
from analyzer.record_type import RecordType
from typing import Type
from itertools import count
from analyzer.csv_worker import dump_vocabulary
from logging import Logger


# To speed up features obtaining better to keep them in numpy arrays.
# In this case we have to know size or record and position of features in vector before start to parse them.
# 'FeaturesKeeper' is a base class for types.


class Features(Enum):
    """
    Enum of supported features. Fields are implemented to be used as indexes in records arrays.
    Can be extended with code like (on GIT parser example):
    `GitFeatures = Features.build_extension('GitFeatures', 'GIT_LINE_TYPE', 'GIT_PIECES_NUMBER', 'GIT_LINE_LENGTH')`
    class GitFeaturesKeeper(FeaturesKeeper):
        def __init__(self):
            super().__init__(RecordType.GIT, GitFeatures)`
    """
    RC_ID = 0

    @staticmethod
    def build_extension(extension_name: str, new_names: []):
        fields = [m.name for m in Features] + new_names
        return Enum(extension_name, zip(fields, count()))


class FeaturesKeeper:
    """
    Class to handle features list. Should be associated with single 'Features' class.
    Provides ability to keep features for one record in Numpy array of pre-known size, build template for such record
    and set values into record array with `record[FooFeatures.BAR.value] = some` syntax.
    I.e. defining one feature takes constant time and doesn't depend from count of features.
    Also it handles list-based features. See `add_vocabulary_feature_value` method.
    """

    record_type: RecordType
    features: Type[Features]
    vocabulary_features: np.ndarray

    def __init__(self, record_type: RecordType, features: Type[Features]):
        self.record_type = record_type
        self.features = features
        self.vocabulary_features = np.empty(len(self.features), dtype=object)
        self.vocabulary_features.fill(None)

    def get_features_names(self):
        features = []
        for feature in self.features:
            features.append(feature.name)
        return features

    def get_feature_names(self):
        return [m.name for m in self.features]

    def get_row_container(self):
        """
        :return: Numpy array for one record with 0 values for all features.
        """
        return np.zeros(len(self.features), dtype=int)

    def add_vocabulary_feature_value(self, feature, vocabulary_item, record: np.ndarray):
        feature_vocabulary: dict = self.vocabulary_features[feature.value]
        if feature_vocabulary is None:
            feature_vocabulary = dict()
            feature_vocabulary[vocabulary_item] = 0  # Index is 0 because dictionary has only one key.
            self.vocabulary_features[feature.value] = feature_vocabulary
            record[feature.value] = 0  # It is index in feature_vocabulary.
        else:
            index = feature_vocabulary.get(vocabulary_item)
            if index is None :
                index = len(feature_vocabulary)  # Dictionary is appended only so calculate unique index from length.
                feature_vocabulary[vocabulary_item] = index
            record[feature.value] = index

    def dump_vocabulary_features(self, logger: Logger):
        features_names = np.array([x.name for x in self.features], dtype=object)
        for feature_index, feature_vocabulary in enumerate(self.vocabulary_features):
            if feature_vocabulary is not None:
                feature_name = features_names[feature_index]
                logger.info("  dump %s feature vocabulary with %d items", feature_name, len(feature_vocabulary))
                dump_vocabulary(feature_name, feature_vocabulary)
