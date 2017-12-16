from analyzer.git_dao import *
from analyzer.csv_worker import FileDumper
from logging import Logger
from analyzer.records_producer import RecordsProducer
from analyzer.csv_worker import dump_vocabulary
import sys
import random
from datetime import datetime


class RecordHandler(object):
    """
    Keep records during analyzing and dump records to file(s). Works with records only one type.
    For one session of analyzing need to create and use few handlers - one per each record type.
    """
    __slots__ = ['record_type', 'producer', 'file_dumper', '_records', 'flushed_records_number']

    def __init__(self, producer: RecordsProducer, file_dumper: FileDumper):
        self.record_type = producer.record_type
        self.producer = producer
        self.file_dumper = file_dumper
        self._records = []
        self.flushed_records_number = 0

    def analyze(self, git_file: GitFile, is_diff_hunk, rc_id: int = -1) -> int:
        """
        Analyzes specified 'GitFile' and saves resulting records into inner 'records'.
        :param git_file: 'GitFile' to analyze.
        :param is_diff_hunk: Flag that 'GitFile' contains "diff_hunk" instead of usual diff.
        :param rc_id: RawComment ID if exist.
        :return: Count of records produced from specified git file.
        """
        records = self.producer.analyze_git_file_recursively(git_file, is_diff_hunk)
        if rc_id > 0:
            for record in records:
                record[self.producer.features.RC_ID] = rc_id
        self._records.extend(records)  # Support case when 'analyze' called few times before 'clean_records' call.
        return len(records)

    def clean_records(self):
        self._records = []

    def flush_records(self, logger: Logger) -> int:
        """
        Flushes internally saved records into file.
        :param logger: Logger to use.
        :return: Number of flushed records.
        """
        records = self._records
        records_len = len(records)
        if records_len > 0:
            logger.debug("  dump %d bytes for %d records list with %d features each", sys.getsizeof(records),
                         len(records), len(records[0]))
            self.file_dumper.flush_records(records)
            self.clean_records()
            self.flushed_records_number += records_len
        return records_len

    def dump_vocabulary_features(self, logger: Logger):
        """
        Dumps vocabulary features into files.
        :param logger: Logger to use.
        """
        for feature_index, feature_vocabulary in enumerate(self.producer.vocabulary_features):
            if feature_vocabulary is not None:
                feature_name = self.producer.features.__slots__[feature_index]
                logger.debug("  dump %s feature vocabulary with %d items", feature_name, len(feature_vocabulary))
                dump_vocabulary(feature_name, feature_vocabulary)

    def finalize_records_file(self, logger: Logger, train_ratio = 0.8):
        """
        Finalizes records files. In details, it:
        - flushes remained records into file,
        - dumps all "vocabulary features" into 'YYY_vocabulary.csv' files,
        - reads records into RAM as lines,
        - shuffles records-lines,
        - separates records to "train" and "test" parts,
        - writes records to 'XXX_train.csv' and 'XXX_test.csv' files with header rows.
        :param logger: Logger to use.
        :param train_ratio: Ratio of 'train' records in all records.
        """
        # Yes, even if it is single flush for whole analyzing, better to dump "raw" records to file first. Because:
        #   a) it is good to have intermediate results,
        #   b) after read records as lines they would occupy less place in RAM (seems like).
        self.flush_records(logger)
        self.file_dumper.close()
        self.dump_vocabulary_features(logger)
        # Read records into RAM.
        time1 = datetime.now()
        with open(self.file_dumper.file_path, 'r', encoding='utf-8', newline='') as file:
            records = file.readlines()
        records_len = len(records)
        time2 = datetime.now()
        logger.debug("  read %d records from '%s' in %s", records_len, self.file_dumper.file_path, time2-time1)
        # Shuffle records.
        random.shuffle(records)
        time3 = datetime.now()
        logger.debug("  shuffle %d records in %s", records_len, time3-time2)
        # Split to train and test.
        train_len = int(len(records) * train_ratio)
        train_records = records[0: train_len]
        test_records = records[train_len:]
        time4 = datetime.now()
        logger.debug("  split records with ratio %f to train (%d) and test (%d) parts in %s", train_ratio, train_len,
                     records_len-train_len, time4-time3)
        # Write 2 records sets into files.
        self.file_dumper.write_all_records_as_lines_with_head(train_records, test_records,
                                                              self.producer.get_feature_names())
        time5 = datetime.now()
        logger.debug("  write %d train and %d test records into files in %s", len(train_records), len(test_records),
                     time5-time4)
