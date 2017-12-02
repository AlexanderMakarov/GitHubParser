from enum import Enum, auto
import numpy as np
from analyzer.record_type import RecordType
from typing import Type
from itertools import count


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
    """

    record_type: RecordType
    features: Type[Features]

    def __init__(self, record_type: RecordType, features: Type[Features]):
        self.record_type = record_type
        self.features = features

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
