from enum import Enum
from analyzer.features_keeper import Features, FeaturesKeeper


names = [m.name for m in Features] + ['GIT_LINE_TYPE', 'GIT_PIECES_NUMBER', 'GIT_LINE_LENGTH']
GitFeatures = Enum('GitFeatures', names)


class GitFeaturesKeeper(FeaturesKeeper, "GIT", GitFeatures):

    def __init__(self, source_type: str, features: Features):
        self.source_type = source_type
        self.features = features
