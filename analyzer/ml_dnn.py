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
from analyzer.git_analyze import parse_git_diff

my_path = os.path.realpath(__file__)
logs_path = os.path.join(my_path, "..", "..", "instance", "tflogs")


def _add_file_features(file: GitFile, input_features, is_only_last_line=False):
    features = []
    file_level_features = input_features.copy()
    file: GitFile
    file_level_features["git_is_%s" % file.file_type] = True
    file_level_features["git_is_file_%s" % file.file_path] = True
    for piece in file.pieces:
        piece_level_features = file_level_features.copy()
        piece: GitPiece
        # Set what to handle.
        lines = piece.lines
        if is_only_last_line:
            lines = lines[:-1]
        # Handle chosen lines.
        for line in lines:
            line_level_features = piece_level_features.copy()
            # line_level_features["raw_comment_id"] = 0  # TODO extract from 'item"
            line: GitLine
            line_raw: str = None  # Line without first +/-/  char.
            if line.type is GitLineType.ADD:
                line_level_features["git_line_type"] = 1
                line_raw = line.line[1:]
            elif line.type is GitLineType.UNCHANGED:
                line_level_features["git_line_type"] = 0
                line_raw = line.line
            else:
                line_level_features["git_line_type"] = -1
                line_raw = line.line[1:]
            line_level_features["git_line_length"] = len(line_raw)
            # TODO add more features.
            features.append(line_level_features)  # Save features.
    return features


def get_git_features_from_rcs(rcs: []):
    result = []
    for rc in rcs:
        rc: RawComment
        git_file = parse_git_diff(rc.diff_hunk, rc.path)
        assert len(git_file) == 1, "parse_git_diff returns not 1 GitFile"
        features = {"rc_id": str(rc.id)}
        all_lines_features = _add_file_features(git_file[0], features, True)
        assert len(all_lines_features) == 1, "_add_file_features returns not 1 futures set"
        features.update(all_lines_features[0])
        result.append(features)
    return result


def get_git_features_from_prs(prs: []):
    files = []
    # Pre-get files because all of them without positive output - raw comments. It decreases RAM usage.
    for pr in prs:
        pr: PullRequest
        git_files = parse_git_diff(pr.diff, None)
        files.append(git_files)
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
    for file in files:
        features = {"rc_id": -1}  # Assume that all lines received from PR has no comments.
        result.append(_add_file_features(file, features))
    return result


def parse_and_dump_features(rcs: [], prs: [], sess):
    # 1) First from PR-s
    prs_features = get_git_features_from_prs(prs)
    # 2) Next from RC-s
    rcs_features = get_git_features_from_rcs(rcs)
    # 3) collect features together and split to train and test.
    all_features = prs_features.extend(rcs_features)
    tt = sess.run(tf.random_shuffle(all_features))



    pass


def dump_outputs(logger: Logger, raw_comments: []):
    return classify_and_dump_raw_comments(logger, raw_comments)


def preanalyze(logger: Logger, raw_comments: [], pull_requests: []):
    # 1) get outputs.
    outputs_csv_path = dump_outputs(logger, raw_comments)
    # 2) get features


    # 3) prepare training sets.
    """training_set = tf.contrib.learn.datasets.base.load_csv_with_header(
        filename=outputs_csv_path,
        target_dtype=np.int,
        features_dtype=np.float32)
    test_set = tf.contrib.learn.datasets.base.load_csv_with_header(
        filename=IRIS_TEST,
        target_dtype=np.int,
        features_dtype=np.float32)"""


def some(items: []):
    tf.logging.set_verbosity(tf.logging.INFO)
    # TODO create https://www.tensorflow.org/get_started/estimator
