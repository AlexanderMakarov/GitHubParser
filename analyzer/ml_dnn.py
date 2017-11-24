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
instance_path = os.path.join(my_path, "..", "..", "instance")
logs_path = os.path.join(instance_path, "tflogs")


def _add_file_features(file: GitFile, is_only_last_line=False):
    features = []
    file_level_features = dict()
    file: GitFile
    file_level_features["git_is_%s" % file.file_type] = True
    file_level_features["git_is_file_%s" % file.file_path] = True
    for piece in file.pieces:
        piece_level_features = file_level_features.copy()
        piece: GitPiece
        # Set what to handle.
        lines = piece.lines
        if is_only_last_line:
            lines = lines[-1:]
        # Handle chosen lines.
        for line in lines:
            line_level_features = piece_level_features.copy()
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
    # returns tuple of features and path where RC's were found.
    features_sets = []
    files = set()
    for rc in rcs:
        rc: RawComment
        git_file = parse_git_diff(rc.diff_hunk, rc.path)
        assert len(git_file) == 1, "parse_git_diff returns not 1 GitFile"
        all_lines_features = _add_file_features(git_file[0], True)
        assert len(all_lines_features) == 1, "_add_file_features returns not 1 futures set"
        line_features = all_lines_features[0]
        line_features["rc_id"] = rc.id
        features_sets.append(line_features)
        files.update(rc.path)
    return (features_sets, files)


def get_git_features_from_prs(prs: [], files: []):
    # Analyze only files from list to decrease count of trash files.
    files = []
    # Pre-get files because all of them without positive output - raw comments. It decreases RAM usage.
    for pr in prs:
        pr: PullRequest
        git_files = parse_git_diff(str(pr.diff), None)
        target_git_files = list(filter(lambda x: x.file_path in files, git_files))
        files.extend(target_git_files)
    result = []  # List of rows with full features set.
    for file in files:
        features = _add_file_features(file)
        for line_features in features:
            line_features["rc_id"] = 0
        result.extend(features)
    return result


def parse_and_dump_features(rcs: [], prs: [], sess):
    # 2) First parse RC's to filter PR-s.
    rcs_features, files = get_git_features_from_rcs(rcs)
    # 1) First from PR-s
    prs_features = get_git_features_from_prs(prs, files)
    # 3) collect features together and dump.
    all_features = prs_features.extend(rcs_features)
    feature_names = [x for x in all_features[0]]
    path = dump_features(feature_names, all_features)
    return path


def dump_outputs(logger: Logger, raw_comments: []):
    return classify_and_dump_raw_comments(logger, raw_comments)


def preanalyze(logger: Logger, raw_comments: [], pull_requests: []):
    # 1) get outputs.
    #outputs_csv_path = dump_outputs(logger, raw_comments)
    # 2) get features

    sess = tf.Session()
    features_path = parse_and_dump_features(raw_comments, pull_requests, sess)

    #tt = sess.run(tf.random_shuffle(all_features))
    # 3) prepare training sets.
    common_set = tf.contrib.learn.datasets.base.load_csv_with_header(
            filename=features_path,
            target_dtype=np.int,
            features_dtype=np.int)

    # TODO get all features from set.
    feature_columns = [tf.feature_column.numeric_column("x", shape=[4])]
    classifier = tf.estimator.DNNClassifier(feature_columns=feature_columns,
            hidden_units=[10, 20, 10],
            n_classes=3,
            model_dir=os.path.join(instance_path, "model"))


def some(items: []):
    tf.logging.set_verbosity(tf.logging.INFO)
    # TODO create https://www.tensorflow.org/get_started/estimator
