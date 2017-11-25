from __future__ import print_function
import tensorflow as tf
import numpy as np
import os
from model.git_data import *
from model.raw_comment import RawComment
from model.pull_request import PullRequest
from analyzer.raw_comments_classifier import classify_raw_comments, RCClass, classify_and_dump_raw_comments
from analyzer.csv_worker import dump_features, dump_train, dump_test, TRAIN_CSV_PATH, TEST_CSV_PATH
from logging import Logger, Handler
from analyzer.git_analyze import parse_git_diff
from datetime import datetime
import random
from parsers.xml_parser import XmlParser
from features.xml_features import XmlFeatures


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


def get_features_from_rcs(logger: Logger, rcs: []):
    # returns tuple of features and path where RC's were found.
    features_sets = []
    files = set()
    for rc in rcs:
        rc: RawComment
        git_files = parse_git_diff(rc.diff_hunk, rc.path)
        git_files_len = len(git_files)
        if git_files_len != 1:
            logger.warning("parse_git_diff returns %d GitFile-s from %d raw comment", git_files_len, rc.id)
            continue
        git_file: GitFile = git_files[0]
        # Parse GIT features.
        all_lines_features = _add_file_features(git_file, True)
        assert len(all_lines_features) == 1, "_add_file_features returns not 1 futures set"
        line_features = all_lines_features[0]
        # Parse XML features.
        if git_file.file_type == FileType.XML:
            xml_feature_names = XmlFeatures.get_headers()
            parser = XmlParser()
            for piece in git_file.pieces:
                last_line_type = piece.lines[len(piece.lines) - 1].type
                lines_arr = []
                for line in piece.lines:
                    if line.type == GitLineType.UNCHANGED or line.type == last_line_type:
                        raw_line = line.line[1:] if line.type is not GitLineType.UNCHANGED else line.line
                        lines_arr.append(raw_line)
                xml_features = parser.parse(lines_arr)[0]
                xml_features_dict = dict(zip(xml_feature_names, xml_features.serialize()))
                line_features.update(xml_features_dict)
        # Add output value - rc_id.
        line_features["rc_id"] = rc.id
        features_sets.append(line_features)
        files.add(rc.path)
    return (features_sets, files)


def get_features_from_prs(prs: [], files: []):
    # Analyze only files from list to decrease count of trash files.
    pr_files = []
    # Pre-get files because all of them without positive output - raw comments. It decreases RAM usage.
    for pr in prs:
        pr: PullRequest
        git_files = parse_git_diff(str(pr.diff), None)
        target_git_files = list(filter(lambda x: x.file_path in files, git_files))
        pr_files.extend(target_git_files)
    result = []  # List of rows with full features set.
    for file in pr_files:
        features = _add_file_features(file)
        for line_features in features:
            line_features["rc_id"] = 0
        result.extend(features)
    return result


def parse_and_dump_features(logger: Logger, rcs: [], prs: [], train_part: float):
    # Returns tuple (feature_names, records_count, path_to_train_file, path_to_test_file)
    # 1) First parse RC's to filter PR-s.
    time1 = datetime.today()
    features, files = get_features_from_rcs(logger, rcs)
    # 2) First from PR-s
    time2 = datetime.today()
    rcs_features_len = len(features)
    logger.info("Analyzed %d raw comments from %d files in %s seconds", rcs_features_len, len(files), time2 - time1)
    prs_features = get_features_from_prs(prs, files)
    time3 = datetime.today()
    # 3) collect features together and dump.
    features.extend(prs_features)
    records_len = len(features)
    logger.info("Analyzed %d more lines from %d pull requests in %s seconds", records_len - rcs_features_len,\
            len(prs), time3 - time2)
    # features: convert list of dicts into list of values.
    feature_names = set()
    for feature in features:
        for name in feature:
            feature_names.add(name)
    feature_names.remove("rc_id")  # Remove output column from feature names.
    feature_names = list(sorted(feature_names))
    logger.info("Total %d features will be used. Find feature names, shuffle and split records.", len(feature_names))
    rows = []
    for feature in features:
        row = []
        row.append(feature["rc_id"])  # Add rc_id (y).
        for name in feature_names:
            row.append(feature[name] if name in feature else 0)
        rows.append(row)
    # Shuffle rows and split to test and train.
    random.shuffle(rows)
    train_len = int(records_len * train_part)
    train_rows = rows[0: train_len]
    test_rows = rows[train_len:]
    time4 = datetime.today()
    logger.info("Total %d training and %d test records prepared in %s seconds", len(train_rows), len(test_rows),\
            time4 - time3)
    # Dump names and rows.
    train_file_path = dump_train(feature_names, train_rows)
    test_file_path = dump_test(feature_names, test_rows)
    logger.info("Dumped all records into '%s' and '%s'", train_file_path, test_file_path)


def dump_outputs(logger: Logger, raw_comments: []):
    return classify_and_dump_raw_comments(logger, raw_comments)


def read_csv(path_to_csv: str, feature_names: []):
    filename_queue = tf.train.string_input_producer(tf.convert_to_tensor([path_to_csv]), shuffle=False)
    line_reader = tf.TextLineReader(skip_header_lines=1)
    _, csv_row = line_reader.read(filename_queue)
    record_defaults = [[0]]  # Add one for rc_id.
    for _ in feature_names:
        record_defaults.append([0])
    record = tf.decode_csv(csv_row, record_defaults=record_defaults)
    record = tf.stack([record])
    return record


def train_net(log_handler: Handler, raw_comments_number: int, steps_number: int):
    #tf.logging.set_verbosity(tf.logging.INFO)
    logger = tf.logging._logger
    if log_handler not in logger.handlers:
        logger.addHandler(log_handler)
    # Define pipelines to parse features from CSVs.
    training_set = tf.contrib.learn.datasets.base.load_csv_with_header(
            filename=TRAIN_CSV_PATH,
            target_dtype=np.int,
            features_dtype=np.int,
            target_column=1)
    test_set = tf.contrib.learn.datasets.base.load_csv_with_header(
            filename=TEST_CSV_PATH,
            target_dtype=np.int,
            features_dtype=np.int,
            target_column=1)
    # Define net.
    features_number = training_set.data.shape[1]
    feature_columns = [tf.feature_column.numeric_column("x", shape=[features_number])]
    classifier = tf.estimator.DNNClassifier(feature_columns=feature_columns,
            hidden_units=[200, 400, 200],  # TODO magic numbers
            n_classes=raw_comments_number,
            model_dir=os.path.join(instance_path, "model"))
    # Define the training inputs.
    train_len = len(training_set.data)
    train_input_fn = tf.estimator.inputs.numpy_input_fn(
            x={"x": np.array(training_set.data)},
            y=np.array(training_set.target),
            num_epochs=None,
            shuffle=False)
    # Train model.
    time1 = datetime.today()
    logger.info("Start training for %d records each %d features %s steps", train_len, features_number, steps_number)
    classifier.train(input_fn=train_input_fn, steps=steps_number)
    time2 = datetime.today()
    logger.info("Training takes %s seconds", time2 - time1)
    # Define the test inputs.
    test_len = len(test_set.data)
    test_input_fn = tf.estimator.inputs.numpy_input_fn(
            x={"x": np.array(test_set.data)},
            y=np.array(test_set.target),
            num_epochs=1,
            shuffle=False)
    # Evaluate accuracy.
    logger.info("Start test accuracy for %d records each %d features", test_len, features_number)
    accuracy_score = classifier.evaluate(input_fn=test_input_fn)["accuracy"]
    time3 = datetime.today()
    logger.info("Test accuracy is %f. Takes %s seconds.", accuracy_score, time3 - time2)
