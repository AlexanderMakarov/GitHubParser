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
    parser = argparse.ArgumentParser(description='Analyzes required RCs and PRs.')
    parser.add_argument('rcs', type=int, nargs='?', help='Raw Comments count.')
    parser.add_argument('prs', type=int, nargs='?', help='Pull Requests count.')
    args = parser.parse_args()
    print("rcs=%d, prs=%d" % (args.rcs, args.prs))

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
    analyzer = Analyzer(GitRecordsProducer())
    # TODO analyzer = Analyzer(GitRecordsProducer(), XmlRecordsProducer(), SwiftRecordsProducer())
    # Start analyze.
    time2 = datetime.today()
    logger.info("Load %d raw comments and %d pull requests in %s.", len(raw_comments), len(prs),
                time2 - time1)
    # Analyze and write to CSV files.
    records_count = analyzer.analyze_items(logger, raw_comments, multiprocessing.cpu_count())
    time3 = datetime.today()
    logger.info("Analyzed %d records from %d raw comments in %s.", records_count, len(raw_comments),
                time3 - time2)
    records_count = analyzer.analyze_items(logger, prs, multiprocessing.cpu_count())
    analyzer.finalize()
    time4 = datetime.today()
    logger.info("Analyzed %d records from %d pull requests in %s.", records_count, len(prs),
                time4 - time3)
