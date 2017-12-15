from analyzer.git_dao import *
from analyzer.csv_worker import FileDumper
from logging import Logger
from analyzer.records_producer import RecordsProducer
from analyzer.csv_worker import dump_vocabulary
import sys


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
        for feature_index, feature_vocabulary in enumerate(self.producer.vocabulary_features):
            if feature_vocabulary is not None:
                feature_name = self.producer.features.__slots__[feature_index]
                logger.info("  dump %s feature vocabulary with %d items", feature_name, len(feature_vocabulary))
                dump_vocabulary(feature_name, feature_vocabulary)

    def finalize_records_file(self, logger: Logger):
        self.flush_records(logger)
        self.file_dumper.write_head(self.flushed_records_number, self.producer.get_feature_names())
        self.dump_vocabulary_features(logger)