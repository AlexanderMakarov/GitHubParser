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
from logging import Handler
import logging.handlers
from threading import Thread


class HomeView(BaseView):
    route_base = "/"

    @appbuilder.app.errorhandler(404)
    def page_not_found(self):
        return render_template('404.html', base_template=appbuilder.base_template, appbuilder=appbuilder), 404


class BufferLogHandler(Handler):
    buffer_size = 100
    buffer = []

    def emit(self, record):
        log_entry = self.format(record)
        if len(self.buffer) < self.buffer_size - 1:
            self.buffer.append(log_entry)
        elif len(self.buffer) < self.buffer_size:
            self.buffer.append("------------ limit of logs reached --------------")

    def get_buffer_and_reset(self):
        result = self.buffer[:]
        self.buffer = []
        return result


memoryhandler: BufferLogHandler = None
fetch_status = 0  # 0 - not started yet, 1 - in progress, 2 - finished.


@app.route("/fetch", methods=['POST'])
def fetch_with_params():
    number = -1  # '-1' means "all".
    if 'number' in request.form:
        number = int(request.form['number'])
    global fetch_status
    fetch_status = 1
    thread = Thread(name="fetch rc", target=fetch, args=[number])
    thread.start()
    return "fetch: number=%d" % number


def fetch(number):
    # Prepare log grabber.
    global memoryhandler
    memoryhandler = BufferLogHandler()
    app.logger.addHandler(memoryhandler)
    global fetch_status
    fetch_status = 1
    time1 = datetime.today()
    raw_comments = get_raw_comments_from_github(app.logger, app.config['ACCOUNTS'], app.config['REPO'],
            app.config['REPO_OWNER'], number)
    time2 = datetime.today()
    resulting_count = len(raw_comments)
    app.logger.info("Fetched %d raw comments in %s seconds", resulting_count, time2 - time1)
    db.session.add_all(raw_comments)
    db.session.commit()
    app.logger.info("Saved %d raw comments into database", resulting_count)
    fetch_status = 2
    return "done"


@app.route("/fetch/log")
def fetch_log():
    logs = memoryhandler.get_buffer_and_reset()
    result = ""
    for line in logs:
        result += str(line) + "\n"
    if len(result) == 0 and fetch_status == 2:  # If fetch finished then send EOF.
        return "EOF"
    return result
    #return "log %s" + str(random.random())


class RawCommentView(ModelView):
    route_base = "/raw_comments"
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
    route_base = "/prs"
    datamodel = SQLAInterface(Comment)
    search_exclude_columns = ["id"]

    @expose("/prs")
    def prs(self):
        return "prs"

    @expose("/prs/<int:pr_id>")
    def pr(self, pr_id):
        return "prs/" + str(pr_id)


db.create_all()
#appbuilder.add_view(HomeView, "Home", category="Home")
appbuilder.add_view(RawCommentView, "List fetched comments", category="Raw Comments")
appbuilder.add_view(CommentView, "List Comments", category="Comments")
appbuilder.add_view(PullRequestsView, "List Pull Requests", category="Pull Requests")