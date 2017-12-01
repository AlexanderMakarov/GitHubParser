from enum import Enum, auto
import numpy as np
from analyzer.record_type import RecordType


# To speed up features obtaining better to keep them in numpy arrays.
# In this case we have to know size or record and position of features in vector before start to parse them.
# 'FeaturesKeeper' is a base class for types.


class Features(Enum):
    RC_ID = auto()


class FeaturesKeeper:
    record_type: RecordType
    features: Features

    def __init__(self, record_type: RecordType, features: Features):
        self.record_type = record_type
        self.features = features

    def get_features_names(self):
        features = []
        for feature in self.features:
            features.append(feature.name)
        return features

    def get_row_container(self):
        return np.empty(len(self.features), dtype=int)
