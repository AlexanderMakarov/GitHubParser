from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import argparse
import sys
import logging
import multiprocessing
from config import SQLALCHEMY_DATABASE_URI
from datetime import datetime
from model.raw_comment import RawComment
from model.pull_request import PullRequest
from analyzer.analyzer import Analyzer
from analyzer.git.git_producer import GitRecordsProducer
from analyzer.ml import MachineLearning, Prediction


if __name__ == '__main__':
    # Parse command line arguments.
    parser = argparse.ArgumentParser(description='Trains networks on prepared (analyzed) records and predicts specified'
                                                 ' PR comments.')
    parser.add_argument('steps_count', type=int, nargs='?', default=100, help='Train steps count for all networks.')
    parser.add_argument('pr', type=int, nargs='?', default=1311, help='Pull Request to predict.')
    args = parser.parse_args()

    # Connect db.
    Session = sessionmaker(autoflush=False)
    engine = create_engine(SQLALCHEMY_DATABASE_URI)
    Session.configure(bind=engine)
    session = Session()

    # Create logger.
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
    logger = logging.getLogger("analyzer")

    # Build analyzer.
    analyzer = Analyzer(logger, False, GitRecordsProducer())
    # TODO analyzer = Analyzer(logger, args.chunks, GitRecordsProducer(), XmlRecordsProducer(), SwiftRecordsProducer())
    ml = MachineLearning(analyzer, None, analyzer.get_raw_comments_number())
    # Train network.
    time1 = datetime.today()
    ml.train(args.steps_count)
    time2 = datetime.today()
    logger.info("Trained network in %s.", time2 - time1)
    # Predict PR lines.
    pr = session.query(PullRequest).filter(PullRequest.id == args.pr).first()
    predictions = ml.predict(pr)
    time3 = datetime.today()
    logger.info("Got %d predictions for each line in %d pull request in %s.", len(predictions), args.pr,
                time3 - time2)
    for prediction in predictions:
        prediction: Prediction
        possible_rc_indexes = prediction.get_indexes_more_than(0.0001)  # Because ratio is 0.999687 (5611 vs 17892763).
        if len(possible_rc_indexes) > 0:
            possible_rc_indexes = sorted(possible_rc_indexes, reverse=True)
            print(prediction.line)
            for possibility, index in possible_rc_indexes:
                print("    %f[%d]: %s", possibility, index, "TODO get message")
