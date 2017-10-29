from flask import render_template, request
from flask_appbuilder.models.sqla.interface import SQLAInterface
from flask_appbuilder import AppBuilder, ModelView, expose, BaseView, has_access, action
from webapp import appbuilder, app, db
from datetime import datetime
from github_parser.parser import get_raw_comments_from_github
from model.raw_comment import RawComment
from model.comment import Comment
import time
import random
import logging
import logging.handlers
from threading import Thread


class HomeView(BaseView):
    route_base = "/"

    @appbuilder.app.errorhandler(404)
    def page_not_found(self):
        return render_template('404.html', base_template=appbuilder.base_template, appbuilder=appbuilder), 404

    """@expose("/")
    @expose("/home")
    def home(self):
        return render_template("index.html")"""


class FetchView(BaseView):
    route_base = "/fetch"
    datamodel = SQLAInterface(RawComment)
    memoryhandler = None  # Handler to get logs during "/log" calls.
    # https://docs.python.org/3/library/logging.handlers.html#logging.handlers.MemoryHandler

    #@expose("/", methods=['POST'])
    #@app.route("/fetch", methods=['POST'])
    #@has_access
    def fetch_with_params(self):
        number = -1  # '-1' means "all".
        if 'number' in request.form:
            number = int(request.form['number'])
        return self.fetch(number)

    #@expose("/<int:count>")
    #@has_access
    def fetch(self, number):

        print("Inside fetch handlerdd")  # TODO remove

        # Prepare log grabber.
        self.memoryhandler = logging.handlers.MemoryHandler(
            capacity=1024 * 100,
            flushLevel=logging.ERROR,
            target=app.logger
        )
        time1 = datetime.today()
        raw_comments = get_raw_comments_from_github(app.logger, app.config['ACCOUNTS'], app.config['REPO'],
                app.config['REPO_OWNER'], number)
        time2 = datetime.today()
        resulting_count = len(raw_comments)
        app.logger.info("Fetched %d raw comments in %d seconds", resulting_count, int(time2 - time1))
        self.datamodel.session.bulk_save_objects(raw_comments)
        self.datamodel.session.commit()
        app.logger.info("Saved %d raw comments into database", resulting_count)
        return "done"

    #@app.route("/fetch/log")
    #@has_access
    def fetch_log(self):

        print("Inside log handler")  # TODO remove

        # TODO return and flush self.memoryhandler if not None

        # text/html is required for most browsers to show the partial page immediately.
        return "log %d" + random.random()


memoryhandler = None


@app.route("/fetch", methods=['POST'])
def fetch_with_params():
    number = -1  # '-1' means "all".
    if 'number' in request.form:
        number = int(request.form['number'])
    thread = Thread(name="fetch rc", target=fetch, args=[number])
    thread.start()
    return "fetch: number=%d" % number


def fetch(number):

    print("Inside fetch handler")  # TODO remove

    # Prepare log grabber.
    global memoryhandler
    memoryhandler = logging.handlers.MemoryHandler(  # TODO doesn't work - cannot read from it.
        capacity=1024 * 100,
        flushLevel=logging.ERROR,
        target=app.logger
    )
    time1 = datetime.today()
    raw_comments = get_raw_comments_from_github(app.logger, app.config['ACCOUNTS'], app.config['REPO'],
            app.config['REPO_OWNER'], number)
    time2 = datetime.today()
    resulting_count = len(raw_comments)
    app.logger.info("Fetched %d raw comments in %s seconds", resulting_count, time2 - time1)
    db.session.add_all(raw_comments)
    db.session.commit()
    app.logger.info("Saved %d raw comments into database", resulting_count)
    return "done"


@app.route("/fetch/log")
def fetch_log():

    print("Inside /fetch/log handler")  # TODO remove

    # TODO return and flush self.memoryhandler if not None

    return "log %s" + str(random.random())


class RawCommentView(ModelView):
    route_base = "/rawcomments"
    datamodel = SQLAInterface(RawComment)
    search_exclude_columns = ["id"]


class CommentView(ModelView):
    route_base = "/comments"
    datamodel = SQLAInterface(Comment)
    search_exclude_columns = ["id"]

    @expose("/comments")
    def comments(self):
        return "comments"

    @expose("/comments/<int:comment_id>")
    def comment(self, comment_id):
        return "comments/" + str(comment_id)


class PullRequestsView(ModelView):
    route_base = "/pr"
    datamodel = SQLAInterface(Comment)
    search_exclude_columns = ["id"]

    @expose("/prs")
    def prs(self):
        return "prs"

    @expose("/prs/<int:pr_id>")
    def pr(self, pr_id):
        return "prs/" + str(pr_id)


class LogView(BaseView):
    route_base = "/log"

    @app.route("/log")
    def log(self):

        print("Inside log handler")  # TODO remove

        # TODO make log provider

        # text/html is required for most browsers to show the partial page immediately.
        return "log %d" + random.random()


db.create_all()
#appbuilder.add_view(HomeView, "Home", category="Home")
appbuilder.add_view_no_menu(LogView())
appbuilder.add_view(RawCommentView, "List fetched comments", category="Raw Comments")
appbuilder.add_view(CommentView, "List Comments", category="Comments")
appbuilder.add_view(PullRequestsView, "List Pull Requests", category="Pull Requests")
appbuilder.add_view_no_menu(FetchView, "Fetch")