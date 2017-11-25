from __future__ import print_function
import tensorflow as tf
import numpy as np
import os
from model.git_data import *
from model.raw_comment import RawComment
from model.pull_request import PullRequest
from analyzer.raw_comments_classifier import classify_raw_comments, RCClass, classify_and_dump_raw_comments
from analyzer.csv_worker import dump_features, dump_train, dump_test, get_test_csv_path, get_train_csv_path
from logging import Logger, Handler
from analyzer.git_analyze import parse_git_diff
from datetime import datetime
import random
from parsers.xml_parser import XmlParser
from features.xml_features import XmlFeatures
from parsers.swift_parser import SwiftParser
from features.swift_features import SwiftFeatures
from enum import Enum
from analyzer.csv_worker import get_two_lines_of_test_file


my_path = os.path.realpath(__file__)
instance_path = os.path.join(my_path, "..", "..", "instance")
logs_path = os.path.join(instance_path, "tflogs")


class NetType(Enum):
    XML = "XML"
    SWIFT = "SWIFT"
    ANY = "ANY"


class NetKeeper:
    classifier: None
    net_type: NetType = None
    feature_names: [] = []
    raw_comments_number: int = 0

    def __init__(self, net_type, classifier, feature_names, raw_comments_number):
        self.net_type = net_type
        self.classifier = classifier
        self.feature_names = feature_names
        self.raw_comments_number = raw_comments_number

    @staticmethod
    def get_feature_columns(net_type: NetType):
        first_row, second_row = get_two_lines_of_test_file(net_type.value)
        feature_names = first_row[2:]
        features_number = len(second_row) - 1
        return [tf.feature_column.numeric_column("x", shape=[features_number])], feature_names

    @staticmethod
    def get_for_type(log_handler: Handler, net_type: NetType, raw_comments_number: int):
        if net_type in net_keepers:
            return net_keepers[net_type]
        else:
            logger = tf.logging._logger
            if log_handler not in logger.handlers:
                logger.addHandler(log_handler)
            feature_columns, feature_names = NetKeeper.get_feature_columns(net_type)
            classifier = tf.estimator.DNNClassifier(feature_columns=feature_columns,
                                                    hidden_units=[200, 400, 200],  # TODO magic numbers
                                                    n_classes=raw_comments_number,
                                                    model_dir=os.path.join(instance_path, net_type.value + "_model"))
            keeper = NetKeeper(net_type, classifier, feature_names, raw_comments_number)
            net_keepers[net_type] = keeper
            return keeper


net_keepers = dict()


def check_binary_line(line: str):
    return "\x00" in line or any(ord(x) > 0x80 for x in line)


def _add_git_file_features(file: GitFile, is_only_last_line=False):
    # Adds "line_raw" value which is not a feature!
    features_list = []
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
        is_first_line = True
        for line in lines:
            if is_first_line:
                is_first_line = False
                if check_binary_line(line.line) is None:
                    break  # Don't check binary files.
            line_level_features = piece_level_features.copy()
            line: GitLine
            line_raw: str = line.line  # Line without first +/-/  char.
            if line.type is GitLineType.ADD:
                line_level_features["git_line_type"] = 1
                line_raw = line_raw[1:]
            elif line.type is GitLineType.UNCHANGED:
                line_level_features["git_line_type"] = 0
            else:
                line_level_features["git_line_type"] = -1
                line_raw = line_raw[1:]
            line_level_features["git_line_length"] = len(line_raw)
            line_level_features["line_raw"] = line_raw
            # TODO add more features.
            features_list.append(line_level_features)  # Save features.
    return features_list


def get_features_from_rcs(logger: Logger, rcs: []):
    # returns tuple:
    # xml features
    # swift features
    # any features
    # rcs_file_paths
    xml_features_list = []
    swift_features_list = []
    any_features_list = []
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
        all_lines_features = _add_git_file_features(git_file, True)
        assert len(all_lines_features) == 1, "_add_file_features returns not 1 futures set"
        any_features_dict = all_lines_features[0]
        # Add output value - rc_id.
        any_features_dict["rc_id"] = rc.id
        any_features_dict.pop('line_raw', None)  # Remove extra key.
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
                xml_features_dict.update(any_features_dict)
            xml_features_list.append(xml_features_dict)
        # Parse Swift features.
        elif git_file.file_type == FileType.SWIFT:
            swift_feature_names = SwiftFeatures.get_headers()
            swift_parser = SwiftParser()
            for piece in git_file.pieces:
                last_line_type = piece.lines[len(piece.lines) - 1].type
                lines_arr = []
                for line in piece.lines:
                    if line.type == GitLineType.UNCHANGED or line.type == last_line_type:
                        raw_line = line.line[1:] if line.type is not GitLineType.UNCHANGED else line.line
                        lines_arr.append(raw_line)
                swift_features = swift_parser.parse(lines_arr)[0]
                swift_features_dict = dict(zip(swift_feature_names, swift_features.serialize()))
                swift_features_dict.update(any_features_dict)
            swift_features_list.append(swift_features_dict)
        else:
            any_features_list.append(any_features_dict)
        files.add(rc.path)
    return xml_features_list, swift_features_list, any_features_list, files


def _shrink_list_randomly(items, ratio: float):
    required_number = int(len(items) * ratio)
    return random.sample(items, required_number)


def get_features_from_prs(prs: [], files: []):
    # Analyze only files from list to decrease count of trash files.
    pr_files = []
    # Pre-get files because all of them without positive output - raw comments. It decreases RAM usage.
    for pr in prs:
        pr: PullRequest
        git_files = parse_git_diff(str(pr.diff), None)
        if len(git_files) > 20:
            continue  # Skip really big pull requests.
        if files is not None:
            target_git_files = list(filter(lambda x: x.file_path in files, git_files))
        else:
            target_git_files = git_files
        pr_files.extend(target_git_files)
    xml_features_list = []
    swift_features_list = []
    any_features_list = []
    xml_parser = XmlParser()
    swift_parser = SwiftParser()
    xml_feature_names = XmlFeatures.get_headers()
    swift_feature_names = SwiftFeatures.get_headers()
    for git_file in pr_files:
        any_features_tmp_list = _add_git_file_features(git_file)

        # TODO if use for "predicate" then remember position if patch somehow.

        for any_features_dict in any_features_tmp_list:
            any_features_dict["rc_id"] = 0
            line_raw = any_features_dict.pop('line_raw', None)
            # Parse XML features.
            if git_file.file_type == FileType.XML:
                xml_features_tmp = xml_parser.parse([line_raw])[0]
                xml_features_dict = dict(zip(xml_feature_names, xml_features_tmp.serialize()))
                xml_features_dict.update(any_features_dict)
                xml_features_list.append(xml_features_dict)
            # Parse Swift features.
            elif git_file.file_type == FileType.SWIFT:
                swift_features_tmp = swift_parser.parse([line_raw])[0]
                swift_features_dict = dict(zip(swift_feature_names, swift_features_tmp.serialize()))
                swift_features_dict.update(any_features_dict)
                swift_features_list.append(swift_features_dict)
            else:
                any_features_list.append(any_features_dict)
    # Remove most part of lines because ratio for +/- cases is about 1/10000. Use only 1% of data.
    if files is not None:
        xml_features_list = _shrink_list_randomly(xml_features_list, 0.01)
        swift_features_list = _shrink_list_randomly(swift_features_list, 0.01)
        any_features_list = _shrink_list_randomly(any_features_list, 0.01)
    return xml_features_list, swift_features_list, any_features_list


def get_features_names(records_list: []):
    feature_names = set()
    for record_dict in records_list:
        for name in record_dict:
            feature_names.add(name)
    feature_names.remove("rc_id")  # Remove output column from feature names.
    return list(feature_names)


def shuffle_split_dump_records(logger: Logger, net_name: NetType, records: [], feature_names: [], train_part: float):
    time1 = datetime.today()
    rows = []
    for record_dict in records:
        row = []
        row.append(record_dict["rc_id"])  # Add rc_id (y).
        for name in feature_names:
            row.append(record_dict[name] if name in record_dict else 0)
        rows.append(row)
    # Shuffle rows and split to test and train.
    random.shuffle(rows)
    train_len = int(len(records) * train_part)
    train_rows = rows[0: train_len]
    test_rows = rows[train_len:]
    time2 = datetime.today()
    logger.info("%s: total %d training and %d test records prepared in %s seconds.", net_name.value, len(train_rows),
                len(test_rows), time2 - time1)
    # Dump names and rows.
    train_file_path = dump_train(net_name.value, feature_names, train_rows)
    test_file_path = dump_test(net_name.value, feature_names, test_rows)
    time3 = datetime.today()
    logger.info("%s: dumped all records into '%s' and '%s' in %s seconds.", net_name.value, train_file_path,
                test_file_path, time3 - time2)


def parse_and_dump_features(logger: Logger, rcs: [], prs: [], train_part: float):
    # Returns tuple (feature_names, records_count, path_to_train_file, path_to_test_file)
    # 1) First parse RC's to filter PR-s.
    xml_features = []
    swift_features = []
    any_features = []
    time1 = datetime.today()
    xml_features_list, swift_features_list, any_features_list, files = get_features_from_rcs(logger, rcs)
    xml_features_list_len = len(xml_features_list)
    swift_features_list_len = len(swift_features_list)
    any_features_list_len = len(any_features_list)
    rcs_features_len = xml_features_list_len + swift_features_list_len + any_features_list_len
    # 2) Next from PR-s
    time2 = datetime.today()
    logger.info("Analyzed %d raw comments (%d, %d, %d) from %d files in %s seconds.",
                rcs_features_len, xml_features_list_len, swift_features_list_len, any_features_list_len,
                len(files), time2 - time1)
    prs_xml_features_list, prs_swift_features_list, prs_any_features_list = get_features_from_prs(prs, files)
    xml_features_list_len = len(prs_xml_features_list)
    swift_features_list_len = len(prs_swift_features_list)
    any_features_list_len = len(prs_any_features_list)
    prs_features_len = xml_features_list_len + swift_features_list_len + any_features_list_len
    time3 = datetime.today()
    logger.info("Analyzed %d more lines (%d, %d, %d) from %d pull requests in %s seconds",
                prs_features_len, xml_features_list_len, swift_features_list_len, any_features_list_len,
                len(prs), time3 - time2)
    # 3) collect features together and dump.
    xml_features_list.extend(prs_xml_features_list)
    swift_features_list.extend(prs_swift_features_list)
    any_features_list.extend(prs_any_features_list)
    xml_records_len = len(xml_features_list)
    swift_records_len = len(swift_features_list)
    any_records_len = len(any_features_list)
    records_len = xml_records_len + swift_records_len + any_records_len
    # features: convert list of dicts into list of values.
    xml_features_names = get_features_names(xml_features_list)
    logger.info("For XML files will be used %d features.", len(xml_features_names))
    swift_features_names = get_features_names(swift_features_list)
    logger.info("For SWIFT files will be used %d features.", len(swift_features_names))
    any_features_names = get_features_names(any_features_list)
    logger.info("For remaining files will be used %d features.", len(any_features_names))
    shuffle_split_dump_records(logger, NetType.XML, xml_features_list, xml_features_names, train_part)
    shuffle_split_dump_records(logger, NetType.SWIFT, swift_features_list, swift_features_names, train_part)
    shuffle_split_dump_records(logger, NetType.ANY, any_features_list, any_features_names, train_part)
    time4 = datetime.today()
    logger.info("Dumped all data for all nets in %s seconds.", time4 - time3)


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


def train_net(log_handler: Handler, net_type: NetType, raw_comments_number: int, steps_number: int):
    # Define pipelines to parse features from CSVs.
    training_set = tf.contrib.learn.datasets.base.load_csv_with_header(
            filename=get_train_csv_path(net_type.value),
            target_dtype=np.int,
            features_dtype=np.int,
            target_column=1)
    test_set = tf.contrib.learn.datasets.base.load_csv_with_header(
            filename=get_test_csv_path(net_type.value),
            target_dtype=np.int,
            features_dtype=np.int,
            target_column=1)
    # Define net.
    features_number = training_set.data.shape[1]
    classifier = NetKeeper.get_for_type(log_handler, net_type, raw_comments_number).classifier
    # Define the training inputs.
    train_len = len(training_set.data)
    train_input_fn = tf.estimator.inputs.numpy_input_fn(
            x={"x": np.array(training_set.data)},
            y=np.array(training_set.target),
            num_epochs=None,
            shuffle=False)
    # Train model.
    time1 = datetime.today()
    logger = tf.logging._logger
    logger.info("%s: start training for %d records each %d features %s steps", net_type.value, train_len,
                features_number, steps_number)
    classifier.train(input_fn=train_input_fn, steps=steps_number)
    time2 = datetime.today()
    logger.info("%s: training takes %s seconds", net_type.value, time2 - time1)
    # Define the test inputs.
    test_len = len(test_set.data)
    test_input_fn = tf.estimator.inputs.numpy_input_fn(
            x={"x": np.array(test_set.data)},
            y=np.array(test_set.target),
            num_epochs=1,
            shuffle=False)
    # Evaluate accuracy.
    logger.info("%s: start test accuracy for %d records each %d features", net_type.value, test_len, features_number)
    accuracy_score = classifier.evaluate(input_fn=test_input_fn)["accuracy"]
    time3 = datetime.today()
    logger.info("%s: test accuracy is %f. Takes %s seconds.", net_type.value, accuracy_score, time3 - time2)


def predict(log_handler: Handler, net_type: NetType, pr: PullRequest, raw_comments_number: int):
    # Get net.
    keeper = NetKeeper.get_for_type(log_handler, net_type, raw_comments_number)
    classifier = keeper.classifier
    logger = tf.logging._logger

    # Parse features from PR and dump.
    prs_xml_features_list, prs_swift_features_list, prs_any_features_list = get_features_from_prs([pr], None)
    #predict_csv_path = dump_train("predict_" + str(net_type.value), keeper.feature_names, prs_xml_features_list)
    rows = []
    for record_dict in prs_xml_features_list:
        row = []
        for name in keeper.feature_names:
            row.append(record_dict[name] if name in record_dict else 0)
        rows.append(row)
    # Collect input data for net.
    # predict_set = tf.contrib.learn.datasets.base.load_csv_with_header(
    #         filename=predict_csv_path,
    #         target_dtype=np.int,
    #         features_dtype=np.int)

    new_samples = np.array(rows, dtype=np.int)
    predict_input_fn = tf.estimator.inputs.numpy_input_fn(
            x={"x": new_samples},
            num_epochs=1,
            shuffle=False)

    predictions = list(classifier.predict(input_fn=predict_input_fn))  # 1D tensor same length as input data.
    predicted_classes = [p["classes"] for p in predictions]  # Each 'p' is as dict.
    logger = tf.logging._logger
    for i, item in enumerate(predicted_classes):
        for k, _ in enumerate(item):
            prediction = item[k]
            if prediction > 0.001:
                logger.info("%d line: comment with %d ID possible as %f", i + 1, k, prediction)
    return predicted_classes  # In the same order as input data.
