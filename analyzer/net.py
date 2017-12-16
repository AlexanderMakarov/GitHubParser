from analyzer.record_type import RecordType
from analyzer.csv_worker import get_two_lines_of_test_file
import tensorflow as tf
from analyzer.csv_worker import get_train_csv_path, get_test_csv_path
import numpy as np
from datetime import datetime


class NetKeeper:
    net: None
    net_type: RecordType = None
    raw_comments_number: int = 0

    def __init__(self, net_type: RecordType, net, raw_comments_number: int):
        self.net_type = net_type
        self.net = net
        self.raw_comments_number = raw_comments_number

    @staticmethod
    def get_feature_columns(net_type: RecordType):  # TODO update with vocabulary-based features support.
        first_row, second_row = get_two_lines_of_test_file(net_type.name)
        feature_names = first_row[2:]
        features_number = len(second_row) - 1
        return [tf.feature_column.numeric_column("x", shape=[features_number])], feature_names

    def log_info(self, message: str, *args):
        tf.logging._logger.info("%s: %s" % (self.net_type.name, message), args)

    def train_net(self, steps_number: int):
        # Define pipelines to parse features from CSVs.
        training_set = tf.contrib.learn.datasets.base.load_csv_with_header(
                filename=get_train_csv_path(self.net_type.name),
                target_dtype=np.int,
                features_dtype=np.int,
                target_column=1)
        test_set = tf.contrib.learn.datasets.base.load_csv_with_header(
                filename=get_test_csv_path(self.net_type.name),
                target_dtype=np.int,
                features_dtype=np.int,
                target_column=1)
        # Define the training inputs.
        train_len = training_set.header[0]  # TODO len(training_set.data)
        features_number = training_set.header[1]  # TODO implement.
        train_input_fn = tf.estimator.inputs.numpy_input_fn(
                x={"x": np.array(training_set.data)},
                y=np.array(training_set.target),
                num_epochs=None,
                shuffle=False)
        # Train model.
        time1 = datetime.today()
        self.log_info("start training for %d records each %d features %s steps", train_len, features_number,
                      steps_number)
        self.net.train(input_fn=train_input_fn, steps=steps_number)
        time2 = datetime.today()
        self.log_info("training takes %s", time2 - time1)
        # Define the test inputs.
        test_len = len(test_set.data)
        test_input_fn = tf.estimator.inputs.numpy_input_fn(
                x={"x": np.array(test_set.data)},
                y=np.array(test_set.target),
                num_epochs=1,
                shuffle=False)
        # Evaluate accuracy.
        self.log_info("start test accuracy for %d records each %d features", test_len, features_number)
        accuracy_score = self.net.evaluate(input_fn=test_input_fn)["accuracy"]
        time3 = datetime.today()
        self.log_info("test accuracy is %f. Takes %s.", accuracy_score, time3 - time2)

    def predict(self, features: np.ndarray):
        return self.net.predict_proba(x=features)
