from flask import render_template, request, url_for
from flask_appbuilder.models.sqla.interface import SQLAInterface
from flask_appbuilder import AppBuilder, ModelView, expose, BaseView, has_access, action
from webapp import appbuilder, app, db
from datetime import datetime
from github_parser.parser import get_raw_comments_from_github, PullRequest, fetch_pr_from_github
from model.raw_comment import RawComment
from model.comment import Comment
from flask_wtf import CsrfProtect
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


class FetchView(BaseView):
    route_base = "/fetch"
    logs_keeper: BufferLogHandler = None
    fetch_status = 0  # 0 - not started yet, 1 - in progress, 2 - finished.

    @has_access
    @expose("", methods=['POST'])
    def fetch_with_params(self):
        number = -1  # '-1' means "all".
        if 'number' in request.form:
            number = int(request.form['number'])
        global fetch_status
        fetch_status = 1
        thread = Thread(name="fetch rc", target=FetchView.fetch, args=[self, number])
        thread.start()
        return "fetch: number=%d" % number

    def fetch(self, number):
        # Prepare log grabber.
        self.logs_keeper = BufferLogHandler()
        app.logger.addHandler(self.logs_keeper)
        self.fetch_status = 1
        time1 = datetime.today()
        # Fetch comments from GitHub.
        raw_comments = get_raw_comments_from_github(app.logger, app.config['ACCOUNTS'], app.config['REPO'],
                app.config['REPO_OWNER'], number)
        time2 = datetime.today()
        resulting_count = len(raw_comments)
        app.logger.info("Fetched %d raw comments in %s seconds", resulting_count, time2 - time1)
        # Save comments in db.
        db.session.add_all(raw_comments)
        db.session.commit()
        app.logger.info("Saved %d raw comments into database", resulting_count)
        # Notify 'fetch_log' that process over.
        self.fetch_status = 2
        return "done"
    
    @has_access
    @expose("/log")
    def fetch_log(self):
        logs = self.logs_keeper.get_buffer_and_reset()
        result = ""
        for line in logs:
            result += str(line) + "\n"
        if len(result) == 0 and self.fetch_status == 2:  # If fetch finished then send EOF.
            return "EOF"
        return result


class RawCommentView(ModelView):
    route_base = "/raw_comments"
    datamodel = SQLAInterface(RawComment)
    search_exclude_columns = ["id"]
    page_size = 50


class CommentView(ModelView):
    route_base = "/comments"
    datamodel = SQLAInterface(Comment)
    search_exclude_columns = ["id"]
    page_size = 50

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

    @expose("/prs/<int:pr_id>")
    def pr(self, pr_id):
        return "prs/" + str(pr_id)


class PullRequestView(BaseView):
    route_base = "/pr"

    @has_access
    @expose("", methods=['POST'])
    def open_pr(self):
        pr_number = request.form["number"]
        pr: PullRequest = fetch_pr_from_github(app.logger, app.config['ACCOUNTS'][0], app.config['REPO_OWNER'],\
                app.config['REPO'], pr_number)
        lines = str(pr.diff).split('\\n')
        # TODO save PR's data into database (to check results on local data).
        # Maybe better to parse all pull requests on start for this?
        return render_template("pullrequest.html", base_template = appbuilder.base_template, appbuilder=appbuilder,\
                pr_link=pr.link, pr_number=pr.number, pr_status=pr.status, pr_diff=lines)


class SiteMapView(BaseView):
    route_base = "/site-map"

    def has_no_empty_params(self, rule):
        defaults = rule.defaults if rule.defaults is not None else ()
        arguments = rule.arguments if rule.arguments is not None else ()
        return len(defaults) >= len(arguments)

    @has_access
    @expose("")
    def site_map(self):
        links = []
        for rule in app.url_map.iter_rules():
            if "GET" in rule.methods and SiteMapView.has_no_empty_params(rule):
                url = url_for(rule.endpoint, **(rule.defaults or {}))
                links.append((url, rule.endpoint))
        return render_template("site-map.html", base_template = appbuilder.base_template, appbuilder=appbuilder,\
                links=links)


db.create_all()
#appbuilder.add_view(HomeView, "Home", category="Home")
appbuilder.add_view_no_menu(PullRequestView())
appbuilder.add_view(RawCommentView, "List fetched comments", category="Raw Comments")
appbuilder.add_view(CommentView, "List Comments", category="Comments")
appbuilder.add_view(PullRequestsView, "List Pull Requests", category="Pull Requests")
appbuilder.add_view_no_menu(PullRequestView)
appbuilder.add_view_no_menu(FetchView)
appbuilder.add_view_no_menu(SiteMapView)
