from analyzer.record_type import RecordType
import tensorflow as tf
from analyzer.csv_worker import get_train_csv_path, get_test_csv_path, AnalyzerInfo
import numpy as np
from datetime import datetime


class NetKeeper:
    def __init__(self, net_type: RecordType, net):
        self.net_type: RecordType = net_type
        self.net = net

    def log_info(self, message: str):
        tf.logging._logger.info("%s: %s" % (self.net_type.name, message))

    def train_net(self, analyzer_info: AnalyzerInfo, steps_number: int):
        time1 = datetime.today()
        # Define pipelines to parse features from CSVs.
        training_set = tf.contrib.learn.datasets.base.load_csv_with_header(
                filename=get_train_csv_path(self.net_type.name),
                target_dtype=np.int16,
                features_dtype=np.int16,
                target_column=0)
        test_set = tf.contrib.learn.datasets.base.load_csv_with_header(
                filename=get_test_csv_path(self.net_type.name),
                target_dtype=np.int16,
                features_dtype=np.int16,
                target_column=0)
        # Define the training inputs.
        train_len = len(training_set.data)
        features_number = len(training_set.data.shape[0])
        train_input_fn = tf.estimator.inputs.numpy_input_fn(
                x={"x": np.array(training_set.data)},
                y=np.array(training_set.target),
                num_epochs=None,
                shuffle=False)
        time2 = datetime.today()
        self.log_info("read train and test CSV files as datasets in %s" % (time2 - time1))
        # Train model.
        self.log_info("start training for %d records each %d features %d steps" % (train_len, features_number,
                      steps_number))
        self.net.train(input_fn=train_input_fn, steps=steps_number)
        time3 = datetime.today()
        self.log_info("training takes %s" % (time3 - time2))
        # Define the test inputs.
        test_len = len(test_set.data)
        test_input_fn = tf.estimator.inputs.numpy_input_fn(
                x={"x": np.array(test_set.data)},
                y=np.array(test_set.target),
                num_epochs=1,
                shuffle=False)
        # Evaluate accuracy.
        self.log_info("start test accuracy for %d records each %d features" % (test_len, features_number))
        accuracy_score = self.net.evaluate(input_fn=test_input_fn)["accuracy"]
        time4 = datetime.today()
        self.log_info("test accuracy is %f. Takes %s." % (accuracy_score, time4 - time3))

    def predict(self, features: np.ndarray):
        return self.net.predict_proba(x=features)
