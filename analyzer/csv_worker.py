import csv
import os
import numpy as np
from analyzer.record_type import RecordType
import threading
import queue


my_path = os.path.realpath(__file__)
CSV_FOLDER = os.path.normpath(os.path.join(my_path, "..", "..", "instance", "csv"))
TRAIN_CSV_NAME = "train.csv"
TEST_CSV_NAME = "test.csv"
VOCABULARY_CSV_NAME = "vocabulary.csv"


def _prepare_folder():
    if not os.path.exists(CSV_FOLDER):
        os.makedirs(CSV_FOLDER)


def get_train_csv_path(net_name: str):
    return os.path.join(CSV_FOLDER, "%s_%s" % (net_name, TRAIN_CSV_NAME))


def get_test_csv_path(net_name: str):
    return os.path.join(CSV_FOLDER, "%s_%s" % (net_name, TEST_CSV_NAME))


def get_vocabulary_csv_path(feature_name: str):
    return os.path.join(CSV_FOLDER, "%s_%s" % (feature_name, VOCABULARY_CSV_NAME))


def dump_rcclasses(rcclasses: list):  # TODO remove if is really outdated.
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
    return os.path.join(CSV_FOLDER, "records_%s.csv" % (record_type.name))


class FileDumper:  # Don't use csv_writer because it appends to file by line (slow) and cannot preappend header row.
    def __init__(self, record_type: RecordType):
        self.record_type = record_type
        self.file_path = get_record_file_path(record_type)

    def flush_records(self, records: list):
        np_array = np.asarray(records)
        np.savetxt(self.file_path, np_array, fmt="%d", delimiter=",")

    def write_head(self, flushed_records_number: int, feature_names: list):  # Also closes file.
        names = [str(flushed_records_number), str(len(feature_names))] + feature_names
        head_row = ",".join(names) + "\n"
        # https://stackoverflow.com/questions/5914627/prepend-line-to-beginning-of-a-file
        # https://stackoverflow.com/questions/11645876/how-to-efficiently-append-a-new-line-to-the-starting-of-a-large-file
        self.close()
        with open(self.file_path, 'r+') as file:
            data = file.read()  # Assume we can afford keep whole file content in memory.
            file.seek(0)
            file.write(head_row)
            file.write(data)

    def close(self):
        pass


class ChunksFileDumper(FileDumper):
    def __init__(self, record_type: RecordType):
        super().__init__(record_type)
        self.queue = queue.Queue()
        self.dump_thread = DumpRecordsThread(self.file_path, self.queue)
        self.dump_thread.setDaemon(True)
        self.dump_thread.start()

    def flush_records(self, records: list):
        self.queue.put(records)

    def close(self):
        self.dump_thread.close()


class DumpRecordsThread(threading.Thread):
    def __init__(self, file_path: str, queue: queue.Queue):
        threading.Thread.__init__(self)
        self.is_work = True
        self.is_first = True
        self.queue = queue
        self.file_path = file_path
        self.file = open(self.file_path, 'w', encoding='utf-8', newline='')

    def dump(self, records: list):
        if not self.is_first:
            self.file.write("\n")
        self.is_first = False
        self.file.write("\n".join((",".join((str(x) for x in np.nditer(record))) for record in records)))
        self.file.flush()

    def run(self):
        while self.is_work:
            result = self.queue.get()
            self.dump(result)
            self.queue.task_done()

    def close(self):
        self.queue.join()
        self.is_work = False
        self.file.close()


def dump_vocabulary(feature_name: str, vocabulary: dict):
    _prepare_folder()
    file_path = get_vocabulary_csv_path(feature_name)
    data = "\n".join(k for k in sorted(vocabulary, key=vocabulary.get))
    with open(file_path, 'w', encoding='utf-8', newline='') as file:
        file.write(data)
