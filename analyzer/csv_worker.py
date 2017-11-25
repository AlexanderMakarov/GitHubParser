import csv
import os


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


def normalise_row_values(row):
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


def dump_rcclasses(rcclasses: []):
    _prepare_folder()
    file_path = os.path.join(CSV_FOLDER, "rclasses.csv")
    with open(file_path, 'w', encoding='utf-8', newline='') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["common_message", "raw_comments"])
        for row in rcclasses:
            writer.writerow([row.common_message, row.serialize_raw_comments()])
    return file_path
