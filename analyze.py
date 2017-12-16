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


if __name__ == '__main__':
    # Parse command line arguments.
    parser = argparse.ArgumentParser(description='Analyzes required RCs and PRs. By default all.')
    parser.add_argument('rcs', type=int, nargs='?', default=-1, help='Raw Comments count.')
    parser.add_argument('prs', type=int, nargs='?', default=-1, help='Pull Requests count.')
    parser.add_argument('--chunks', action='store_true',
                        help='Flag to flush records by chunks. It allows to reduce RAM load but slows down analyzing'
                             ' speed more than 2 times.')
    args = parser.parse_args()

    # Connect db.
    Session = sessionmaker(autoflush=False)
    engine = create_engine(SQLALCHEMY_DATABASE_URI)
    Session.configure(bind=engine)
    session = Session()

    # Create logger.
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
    logger = logging.getLogger("analyzer")

    # Get required number of RC-s and PR-s.
    time1 = datetime.today()
    # Use all RCs.
    raw_comments = session.query(RawComment).limit(args.rcs).all()
    # Use only closed PRs.
    prs = session.query(PullRequest).filter(PullRequest.state == "closed").limit(args.prs).all()
    # Build analyzer.
    analyzer = Analyzer(logger, args.chunks, GitRecordsProducer())
    # TODO analyzer = Analyzer(logger, args.chunks, GitRecordsProducer(), XmlRecordsProducer(), SwiftRecordsProducer())
    # Start analyze.
    time2 = datetime.today()
    logger.info("Load %d raw comments and %d pull requests in %s.", len(raw_comments), len(prs),
                time2 - time1)
    # Analyze and write to CSV files.
    rc_records_count = analyzer.analyze_items(raw_comments, multiprocessing.cpu_count())
    time3 = datetime.today()
    logger.info("Got %d records due %d raw comments analyzing in %s.", rc_records_count, len(raw_comments),
                time3 - time2)
    pr_records_count = analyzer.analyze_items(prs, multiprocessing.cpu_count())
    time4 = datetime.today()
    logger.info("Got %d records due %d pull requests analyzing in %s.", pr_records_count, len(prs),
                time4 - time3)
    analyzer.finalize(logger)
    records_count = rc_records_count + pr_records_count
    time5 = datetime.today()
    logger.info("Dumped %d records in %s.", records_count, time5 - time4)
    logger.info("Total %s for analyzing %d raw comments and %d pull requests.", time5 - time1, len(raw_comments),
                len(prs))
    logger.info("Percent of negative records (without RC ID) in all records is %f (%d vs %d).",
                pr_records_count/records_count, rc_records_count, pr_records_count)
