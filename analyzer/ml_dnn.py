from __future__ import print_function
import tensorflow as tf
import numpy as np
import os
from model.git_data import *
from model.raw_comment import RawComment
from model.pull_request import PullRequest
from analyzer.raw_comments_classifier import classify_raw_comments, RCClass, classify_and_dump_raw_comments
from analyzer.csv_worker import dump_features, dump_train, dump_test
from logging import Logger
from analyzer.git_analyze import parse_git_diff
from datetime import datetime
import random


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
        files.add(rc.path)
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


def parse_and_dump_features(logger: Logger, rcs: [], prs: []):
    # Returns tuple (feature_names, records_count, path_to_train_file, path_to_test_file)
    # 1) First parse RC's to filter PR-s.
    time1 = datetime.today()
    features, files = get_git_features_from_rcs(rcs)
    # 2) First from PR-s
    time2 = datetime.today()
    rcs_features_len = len(features)
    logger.info("Analyzed %d raw comments from %d files in %s seconds", rcs_features_len, len(files), time2 - time1)
    prs_features = get_git_features_from_prs(prs, files)
    time3 = datetime.today()
    logger.info("Analyzed %d more lines from %d pull requests in %s seconds", len(features) - rcs_features_len,\
            len(prs), time3 - time2)
    # 3) collect features together and dump.
    features.extend(prs_features)
    records_len = len(features)
    # features: convert list of dicts into list of values.
    feature_names = set()
    for feature in features:
        for name in feature:
            feature_names.add(name)
    feature_names.remove("rc_id")  # Remove output column from feature names.
    feature_names = list(sorted(feature_names))
    logger.info("Total %d features will be used", len(feature_names))
    rows = []
    for feature in features:
        row = []
        row.append(feature["rc_id"])  # Add rc_id (y).
        for name in feature_names:
            row.append(feature[name] if name in feature else 0)
        rows.append(row)
    # Shuffle rows and split to test and train.
    random.shuffle(rows)
    train_len = int(records_len * 0.7)  # TODO magic number
    train_rows = rows[0: train_len]
    test_rows = rows[train_len:]
    time4 = datetime.today()
    logger.info("Total %d training and %d test records prepared in %s seconds", len(train_rows), len(test_rows),\
            time4 - time3)
    # Dump names and rows.
    train_file_path = dump_train(feature_names, train_rows)
    test_file_path = dump_test(feature_names, test_rows)
    logger.info("Dumped all records into '%s' and '%s'", train_file_path, test_file_path)
    return feature_names, train_len, (records_len - train_len), train_file_path, test_file_path


def dump_outputs(logger: Logger, raw_comments: []):
    return classify_and_dump_raw_comments(logger, raw_comments)


def read_csv(path_to_csv: str, feature_names: []):
    filename_queue = tf.train.string_input_producer(tf.convert_to_tensor([path_to_csv]), shuffle=False)
    line_reader = tf.TextLineReader(skip_header_lines=1)
    _, csv_row = line_reader.read(filename_queue)
    record_defaults = [[0]]  # Add one for rc_id.
    for name in feature_names:
        record_defaults.append([0])
    #rc_id, *features = tf.decode_csv(csv_row, record_defaults=record_defaults)
    #features = tf.stack([features])
    #return features, rc_id

    record = tf.decode_csv(csv_row, record_defaults=record_defaults)
    record = tf.stack([record])
    return record


def preanalyze(logger: Logger, raw_comments: [], pull_requests: []):
    # 1) get outputs.
    #outputs_csv_path = dump_outputs(logger, raw_comments)
    # 2) get features

    raw_comments_number = len(raw_comments)
    feature_names, train_len, test_len, path_to_train_file, path_to_test_file = \
            parse_and_dump_features(logger, raw_comments, pull_requests)
    features_number = len(feature_names)

    # 3) prepare training sets.
    #x_train, training_rc_id = read_csv(path_to_csv_file, feature_names)
    #x_test, testing_rc_id = read_csv(os.path.join(instance_path, "test.csv"), feature_names)

    # record_train = read_csv(path_to_train_file, feature_names)
    # record_test = read_csv(path_to_test_file, feature_names)
    # y_train, x_train = tf.split(record_train, [1, features_number], 1)
    # y_test, x_test = tf.split(record_test, [1, features_number], 1)
    training_set = tf.contrib.learn.datasets.base.load_csv_with_header(
            filename=path_to_train_file,
            target_dtype=np.int,
            features_dtype=np.int,
            target_column=1)
    test_set = tf.contrib.learn.datasets.base.load_csv_with_header(
            filename=path_to_test_file,
            target_dtype=np.int,
            features_dtype=np.int,
            target_column=1)

    # TODO get all features from set.
    feature_columns = [tf.feature_column.numeric_column("x", shape=[features_number])]
    classifier = tf.estimator.DNNClassifier(feature_columns=feature_columns,
            hidden_units=[20, 40, 20],  # TODO magic numbers
            n_classes=raw_comments_number,
            model_dir=os.path.join(instance_path, "model"))
    # Define the training inputs
    train_input_fn = tf.estimator.inputs.numpy_input_fn(
        # x={"x": np.array([x_train])},
        # y=np.array([y_train]),
        x={"x": np.array(training_set.data)},
        y=np.array(training_set.target),
        num_epochs=None,
        shuffle=False)

    # Train model.
    time1 = datetime.today()
    steps_number = 100  # TODO magic number
    logger.info("Start training for %d records each %d features %s steps", train_len, features_number, steps_number)
    classifier.train(input_fn=train_input_fn, steps=steps_number)
    time2 = datetime.today()
    logger.info("Training takes %s seconds", time2 - time1)

    # Define the test inputs
    test_input_fn = tf.estimator.inputs.numpy_input_fn(
        # x={"x": np.array(x_test)},
        # y=np.array(y_test),
        x={"x": np.array(test_set.data)},
        y=np.array(test_set.target),
        num_epochs=1,
        shuffle=False)

    # Evaluate accuracy.
    logger.info("Start test accuracy for %d records each %d features", test_len, features_number)
    accuracy_score = classifier.evaluate(input_fn=test_input_fn)["accuracy"]
    time3 = datetime.today()
    logger.info("Test accuracy is %f. Takes %s seconds.", accuracy_score, time3 - time2)


def some(items: []):
    tf.logging.set_verbosity(tf.logging.INFO)
    # TODO create https://www.tensorflow.org/get_started/estimator
