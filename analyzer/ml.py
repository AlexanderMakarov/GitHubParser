from logging import Handler
from analyzer.record_type import RecordType
import numpy as np
from analyzer.net import NetKeeper
from datetime import datetime
import tensorflow as tf
from model.pull_request import PullRequest
from analyzer.git_diff_parser import parse_git_diff
from analyzer.analyzer import Analyzer, analyze_git_file
from analyzer.records_handler import RecordsHandler
from analyzer.git_dao import *
import os


my_path = os.path.realpath(__file__)
instance_path = os.path.join(my_path, "..", "..", "instance")
logs_path = os.path.join(instance_path, "tflogs")


class Prediction:  # Should be placed in list to have indexes same as lines in PR diff.
    line: str
    record: np.ndarray
    net_type: RecordType
    possibilities: np.ndarray  # Vector of floats with size = RC's number.

    def __init__(self, line: str, net_type: RecordType, record: np.ndarray):
        self.line = line
        self.net_type = net_type
        self.record = record

    def set_possibilities(self, xz):
        return xz.get()  # TODO complete.

    def get_indexes_more_than(self, limit: float) -> list:
        indexes = np.where(self.possibilities > limit)
        result = []
        for index in indexes:
            result.append((self.possibilities[index], index))
        return result


class MachineLearning:
    net_keepers: dict
    log_handler: Handler
    analyzer: Analyzer
    raw_comments_number: int

    def __init__(self, analyzer: Analyzer, log_handler: Handler, raw_comments_number: int):
        self.analyzer = analyzer
        self.log_handler = log_handler
        self.raw_comments_number = raw_comments_number
        self.net_keepers = dict()
        for record_type in analyzer.get_supported_types():
            self.net_keepers.update(self.get_net_for_type(record_type))

    def get_net_for_type(self, net_type: RecordType):
        if net_type in self.net_keepers:
            return self.net_keepers[net_type]
        else:
            # Build network.
            # Add logs handler to TensorFlow.
            logger = tf.logging._logger
            if self.log_handler and self.log_handler not in logger.handlers:
                logger.addHandler(self.log_handler)
            # Get feature columns and feature names from record files.
            feature_columns, feature_names = NetKeeper.get_feature_columns(net_type)
            # Build DNNClassifier, i.e. network.
            classifier = tf.estimator.DNNClassifier(feature_columns=feature_columns,
                                                    hidden_units=[5000],  # TODO magic numbers
                                                    n_classes=self.raw_comments_number,
                                                    model_dir=os.path.join(instance_path, net_type.value + "_model"))
            keeper = NetKeeper(net_type, classifier, self.raw_comments_number)
            self.net_keepers[net_type] = keeper
            return keeper

    def analyze_records_from_pr(self, pr: PullRequest) -> list:
        self.analyzer.clean_handlers()
        git_files = parse_git_diff(str(pr.diff), None)
        type_to_handler_dict = self.analyzer.type_to_handler_dict
        pre_predictions = type_to_handler_dict.get(RecordType.GIT)
        records_with_type = []
        for git_file in git_files:
            git_file: GitFile
            file_records_number, record_type = analyze_git_file(pre_predictions, type_to_handler_dict, git_file)
            handler: RecordsHandler = type_to_handler_dict.get(record_type)
            lines = []
            for piece in git_file.pieces:
                piece: GitPiece
                for line in piece.lines:
                    line: GitLine
                    if line.type == GitLineType.ADD:
                        lines.append("+" + line.line)
                    elif line.type == GitLineType.REMOVE:
                        lines.append("-" + line.line)
                    else:
                        lines.append(line.line)
            lines_counter = 0
            for record in handler.get_records():
                records_with_type.append(Prediction(lines[lines_counter], record_type, record))
        return records_with_type

    def train(self, steps_number: int):
        for net_keeper in self.net_keepers:
            net_keeper: NetKeeper
            net_keeper.train_net(steps_number)

    def predict(self, pr: PullRequest) -> list:  # List of Prediction-s.
        # Analyze lines from PR into records.
        # Store result in numpy 1D array where first item - record type, remained items - feature values.
        predictions = self.analyze_records_from_pr(pr)
        for item in predictions:
            item: Prediction
            net_keeper: NetKeeper = self.net_keepers[item.net_type]
            xz = net_keeper.predict(item.record)
            item.set_possibilities(xz)
        return predictions
