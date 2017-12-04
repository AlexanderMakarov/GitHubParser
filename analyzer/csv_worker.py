import csv
import os
import numpy as np
from analyzer.record_type import RecordType
import fileinput


my_path = os.path.realpath(__file__)
CSV_FOLDER = os.path.join(my_path, "..", "..", "instance", "csv")
TRAIN_CSV_NAME = "train.csv"
TEST_CSV_NAME = "test.csv"


def _prepare_folder():
    if not os.path.exists(CSV_FOLDER):
        os.makedirs(CSV_FOLDER)


def get_train_csv_path(net_name: str):
    return os.path.join(CSV_FOLDER, "%s_%s" % (net_name, TRAIN_CSV_NAME))


def get_test_csv_path(net_name: str):
    return os.path.join(CSV_FOLDER, "%s_%s" % (net_name, TEST_CSV_NAME))


def dump_features(names: [], rows: []):
    # names - features names. Row - 2d array, same size as 'names'
    # First columns - features of one type. Last column - output value.
    _prepare_folder()
    file_path = os.path.join(CSV_FOLDER, "features.csv")
    with open(file_path, 'w', encoding='utf-8', newline='') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(names)
        for row in rows:
            writer.writerow(row)
    return file_path


def normalise_row_values(row):  # TODO remove - analyzer should use right values at start.
    data = []
    for value in row:
        if value is False:
            data.append(-1)
        elif value is True:
            data.append(1)
        elif value is None:
            data.append(0)
        else:
            data.append(value)
    return data


def dump_train(net_name: str, feature_names: [], rows: []):
    # names - features names + 1 columns for RCClass identifier. Row - same size as 'names'
    _prepare_folder()
    names = [len(rows), len(feature_names)]
    names.extend(feature_names)
    file_path = get_train_csv_path(net_name)
    with open(file_path, 'w', encoding='utf-8', newline='') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(names)
        for row in rows:
            writer.writerow(normalise_row_values(row))
    return file_path


def dump_test(net_name: str, feature_names: [], rows: []):
    # names - features names + 1 columns for RCClass identifier. Row - same size as 'names'
    _prepare_folder()
    names = [len(rows), len(feature_names)]
    names.extend(feature_names)
    file_path = get_test_csv_path(net_name)
    with open(file_path, 'w', encoding='utf-8', newline='') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(names)
        for row in rows:
            writer.writerow(normalise_row_values(row))
    return file_path


def dump_rcclasses(rcclasses: []):  # TODO remove if is really outdated.
    _prepare_folder()
    file_path = os.path.join(CSV_FOLDER, "rclasses.csv")
    with open(file_path, 'w', encoding='utf-8', newline='') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["common_message", "raw_comments"])
        for row in rcclasses:
            writer.writerow([row.common_message, row.serialize_raw_comments()])
    return file_path


def get_two_lines_of_test_file(net_name: str):
    file_path = get_test_csv_path(net_name)
    with open(file_path, 'r', encoding='utf-8', newline='') as csv_file:
        reader = csv.reader(csv_file)
        values = list(reader)
        return values[0], values[1]


def get_record_file_path(record_type: RecordType):
    return os.path.normpath(os.path.join(CSV_FOLDER, "records_%s.csv" % (record_type.name)))


class FileAppender:  # Don't use csv_writer at all because it writes by line, it is slow.
    def __init__(self, record_type: RecordType):
        self.record_type = record_type
        self.file_path = get_record_file_path(record_type)
        self.csv_file = None
        self.flushed_records_number = 0

    def open_file(self):
        self.csv_file = open(self.file_path, 'w', encoding='utf-8', newline='')

    def write_records(self, records: []):
        if self.csv_file is None:
            self.open_file()
        records_number = len(records)
        for record in records:
            #list_strings = np.char.mod('%d', record)
            list_strings = [str(x) for x in np.nditer(record)]
            row = ",".join(list_strings)
            self.csv_file.write(row + "\n")
        self.csv_file.flush()
        self.flushed_records_number += records_number

    def write_head(self, feature_names: []):  # Also closes file.
        names = [str(self.flushed_records_number), str(len(feature_names))] + feature_names
        head_row = ",".join(names)
        # https://stackoverflow.com/questions/5914627/prepend-line-to-beginning-of-a-file
        # https://stackoverflow.com/questions/11645876/how-to-efficiently-append-a-new-line-to-the-starting-of-a-large-file
        self.close()
        with open(self.file_path, 'r+') as file:
            data = file.read()  # Assume we can afford keep whole file content in memory.
            file.seek(0)
            file.write(head_row + "\n")
            file.write(data)

    def close(self):
        if self.csv_file:
            self.csv_file.close()
            self.csv_file = None
