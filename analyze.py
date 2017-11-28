from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import argparse
import logging
from config import SQLALCHEMY_DATABASE_URI
from datetime import datetime
from model.raw_comment import RawComment
from model.pull_request import PullRequest

if __name__ == '__main__':
    # Parse comman dline arguments.
    parser = argparse.ArgumentParser(description='Analyzes required RCs and PRs.')
    parser.add_argument('rcs', type=int, nargs='?', help='Raw Comments count.')
    parser.add_argument('prs', type=int, nargs='?', help='Pull Requests count.')
    args = parser.parse_args()
    print("rcs=%d, prs=%d" % (args.rcs, args.prs))

    # Connect db.
    engine = create_engine(SQLALCHEMY_DATABASE_URI)
    #print("db path=%s" % engine.)
    DBSession = sessionmaker(bind=engine)
    session = DBSession()

    # Create logger.
    logger = logging.getLogger("analyzer")

    # Get required number of RC-s and PR-s.
    time1 = datetime.today()
    # Use all RCs.
    raw_comments = session.query(RawComment).limit(args.rcs).all()
    # Use only closed PRs.
    prs = session.query(PullRequest).filter(PullRequest.state == "closed").limit(args.prs).all()
    time2 = datetime.today()
    logger.info("Load %d raw comments and %d pull requests in %s seconds.", len(raw_comments), len(prs),
                    time2 - time1)
    # TODO analyze.