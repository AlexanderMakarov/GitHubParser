from __future__ import print_function
import tensorflow as tf
import numpy as np
import os
from model.git_data import *
from model.raw_comment import RawComment
from model.pull_request import PullRequest
from analyzer.raw_comments_classifier import classify_raw_comments, RCClass, classify_and_dump_raw_comments
from analyzer.csv_worker import dump_features
from logging import Logger

my_path = os.path.realpath(__file__)
logs_path = os.path.join(my_path, "..", "..", "instance", "tflogs")


def get_features_from_git_data(items: []):

    files = []  # TODO extract from 'items'
    result = []
    all_features = dict()
    # Extract file-type features.
    for file_type in FileType:
        all_features["is_%s" % file_type] = False
    # Extract file-name features.
    for file in files:
        file: GitFile
        all_features["is_file_" % file.file_name] = False
    # Inherit set of features.
    result = []
    for item in items:
        file = None   # TODO extract from 'item'
        file_level_features = all_features.copy()
        file: GitFile
        file_level_features["is_%s" % file.file_type] = True
        all_features["is_file_" % file.file_name] = True
        for piece in file.pieces:
            piece_level_features = file_level_features.copy()
            piece: GitPiece
            for line in piece.lines:
                line_level_features = piece_level_features.copy()
                line_level_features["raw_comment_id"] = 0  # TODO extract from 'item"
                line: GitLine
                if line.type is GitLineType.ADD:
                    line_level_features["line_type"] = 1
                elif line.type is GitLineType.UNCHANGED:
                    line_level_features["line_type"] = 0
                else:
                    line_level_features["line_type"] = -1
                line_level_features["chars_number"] = len(line.line)
                # TODO add features.
                result.append(line_level_features)  # Save features.
    return result


def parse_and_dump_features(raw_comments: [], pull_requests: []):
    pass


def dump_outputs(logger: Logger, raw_comments: []):
    return classify_and_dump_raw_comments(logger, raw_comments)


def preanalyze(logger: Logger, raw_comments: [], pull_requests: []):
    # 1) get outputs.
    outputs_csv_path = dump_outputs(logger, raw_comments)
    # 2) get features
    #feature_columns = []
    #for raw_comment in raw_comments:
    #    feature_columns.append(tf.feature_column.numeric_column(""))


def some(items: []):
    items_features = get_features_from_git_data(items)
    tf.logging.set_verbosity(tf.logging.INFO)


    # TODO create https://www.tensorflow.org/get_started/estimator