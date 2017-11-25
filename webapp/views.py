from flask import render_template, request, url_for
from flask_appbuilder.models.sqla.interface import SQLAInterface
from flask_appbuilder import AppBuilder, ModelView, expose, BaseView, has_access, action
from webapp import appbuilder, app, db
from datetime import datetime
from github_parser.parser import get_pull_requests_from_github, fetch_pr_from_github
from analyzer.analyzer import analyze_items
from model.raw_comment import RawComment
from model.pull_request import PullRequest
# from model.rcclass import RCClass
from model.comment import Comment
import os
import random
from logging import Handler
from threading import Thread
from analyzer.ml_dnn import train_net, parse_and_dump_features
from analyzer.analyzer import parse_git_diff
from model.git_data import GitLineType
from parsers.SwiftParser import SwiftParser
from parsers.xml_parser import XmlParser


class HomeView(BaseView):
    route_base = "/"

    @appbuilder.app.errorhandler(404)
    def page_not_found(self):
        return render_template('404.html', base_template=appbuilder.base_template, appbuilder=appbuilder), 404


class BufferLogHandler(Handler):
    """
    Class to accumulate logs and return them by request.
    """

    buffer_size = 100
    buffer = []

    def emit(self, record):
        log_entry = self.format(record)
        if len(self.buffer) < self.buffer_size - 1:  # Add line.
            self.buffer.append(log_entry)
        elif len(self.buffer) < self.buffer_size:  # Add log about reached limit.
            self.buffer.append("------------ limit of logs reached --------------")

    def get_buffer_and_reset(self):
        result = list(self.buffer)
        self.buffer.clear()
        return result


class BaseWithLogs(BaseView):
    logs_keeper: BufferLogHandler = None
    progress_stage = 0  # 0 - not started yet, 1 - in progress, 2 - finished.

    def init_logs_keeper(self):
        if self.logs_keeper is None:
            self.logs_keeper = BufferLogHandler()
            app.logger.addHandler(self.logs_keeper)

    def get_logs(self):
        if self.logs_keeper is None:
            return "EOF"
        logs = self.logs_keeper.get_buffer_and_reset()
        result = ""
        for line in logs:
            result += str(line) + "\n"
        if len(result) == 0 and self.progress_stage == 2:  # If fetch finished then send EOF.
            self.progress_stage = 0
            return "EOF"
        return result


class FetchView(BaseWithLogs):
    route_base = "/fetch"

    @has_access
    @expose("", methods=['POST'])
    def fetch_with_params(self):
        number = -1  # '-1' means "all".
        if 'number' in request.form:
            number = int(request.form['number'])
        self.progress_stage = 1
        thread = Thread(name="fetch_from_github", target=FetchView.fetch, args=[self, number])
        thread.start()
        return "fetch: number=%d" % number

    def fetch(self, number):
        self.init_logs_keeper()
        self.progress_stage = 1
        app.logger.info("START: Fetch %d pull requests.", number)
        time1 = datetime.today()
        # Fetch data from GitHub.
        pull_requests = get_pull_requests_from_github(app.logger, app.config['ACCOUNTS'], app.config['REPO'],
                app.config['REPO_OWNER'], number)
        time2 = datetime.today()
        resulting_count = len(pull_requests)
        app.logger.info("Fetched %d pull requests in %s seconds", resulting_count, time2 - time1)
        # Save comments in db.
        db_pull_requests = db.session.query(PullRequest).all()
        db_pull_requests_dict = dict()
        for pr in db_pull_requests:
            db_pull_requests_dict[pr.number] = pr
        pull_requests_to_update_numbers = []
        pull_requests_to_insert = []
        for pr in pull_requests:
            if pr.number in db_pull_requests_dict:
                pull_requests_to_update_numbers.append(pr.number)
            else:
                pull_requests_to_insert.append(pr)
        # Save unique PRs.
        session = db.session
        session.add_all(pull_requests_to_insert)
        session.commit()
        # Update existing PRs if need.
        if len(pull_requests_to_update_numbers) > 0:
            for pr in session.query(PullRequest).filter(PullRequest.number.in_(pull_requests_to_update_numbers)).all():
                pr_with_updates: PullRequest = db_pull_requests_dict[pr.number]
                pr.state = pr_with_updates.state
                pr.diff = pr_with_updates.diff
                pr.raw_comments = pr_with_updates.raw_comments
            session.commit()
        app.logger.info("END: Saved %d pull requests into database (%d inserted, %d updated)",\
                resulting_count, len(pull_requests_to_insert), len(pull_requests_to_update_numbers))
        # Notify 'fetch_log' that process over.
        self.progress_stage = 2
        return "done"

    @has_access
    @expose("/log")
    def fetch_log(self):
        return self.get_logs()


class AnalyzeView(BaseWithLogs):
    route_base = "/analyze"

    @has_access
    @expose("", methods=['POST'])
    def analyze_with_params(self):
        rcs_number = -1  # '-1' means "all".
        prs_number = -1
        train_part = 0.8
        if 'rcs_number' in request.form:
            rcs_number = int(request.form['rcs_number'])
        if 'prs_number' in request.form:
            prs_number = int(request.form['prs_number'])
        if 'train_part' in request.form:
            train_part = float(request.form['train_part'])
            if train_part < 0 or train_part > 1.0:
                app.logger.warning("Wrong train_part=%d", train_part)
                return "Wrong train_part=%d" % train_part
        thread = Thread(name="analyze", target=AnalyzeView.analyze, args=[self, rcs_number, prs_number, train_part])
        thread.start()
        return "train: rcs_number=%d prs_number=%d train_part=%d" % (rcs_number, prs_number, train_part)

    def analyze(self, rcs_number: int, prs_number: int, train_part: float):
        self.init_logs_keeper()
        self.progress_stage = 1
        app.logger.info("START: Analyze %d raw comments and %d pull requests. Records will be split train/test=%d.",
                        rcs_number, prs_number, train_part)
        time1 = datetime.today()
        # Use all RCs.
        raw_comments = db.session.query(RawComment).limit(rcs_number).all()
        # Use only closed PRs.
        prs = db.session.query(PullRequest).filter(PullRequest.state == "closed").limit(prs_number).all()
        time2 = datetime.today()
        app.logger.info("Load %d raw comments and %d pull requests in %s seconds.", len(raw_comments), len(prs),
                        time2 - time1)
        parse_and_dump_features(app.logger, raw_comments, prs, train_part, 'swift')  # TODO: hardcoded
        time3 = datetime.today()
        app.logger.info("END: Analyzed %d raw comments and %d pull request in %s seconds.", len(raw_comments), len(prs),
                        time3 - time2)
        self.progress_stage = 2
        return "done"

    @has_access
    @expose("/log")
    def analyze_log(self):
        return self.get_logs()


class ParseView(BaseWithLogs):
    route_base = "/parse"

    @has_access
    @expose("", methods=['POST'])
    def parse_with_params(self):
        count = -1  # '-1' means "all".
        if 'count' in request.form:
            count = int(request.form['count'])

        thread = Thread(name="parse", target=ParseView.parse, args=[self, count])
        thread.start()
        return "parse: count=%d" % count

    def parse(self, count: int):
        self.init_logs_keeper()
        self.progress_stage = 1
        time1 = datetime.today()
        raw_comments = db.session.query(RawComment).limit(count).all()
        parsed_count = 0
        for rc in raw_comments:
            if rc.path[-3:] == 'xml':
                parsed_count += 1
                lines_arr = []
                git_files = parse_git_diff(rc.diff_hunk, rc.path)
                assert len(git_files) == 1, "parse_git_diff returns not 1 GitFile"
                for file in git_files:
                    assert len(file.pieces) == 1, "git file has more than 1 piece"
                    for piece in file.pieces:
                        line_type = piece.lines[len(piece.lines) - 1].type
                        for line in piece.lines:
                            if line.type == GitLineType.UNCHANGED or line.type == line_type:
                                lines_arr.append(line.line if line.line[0] != '+' and line.line[0] != '-' else line.line[1:])
                parser = XmlParser()
                parsed_results = parser.parse(lines_arr)
                app.logger.info(str(parsed_results[-1:][0]))

        time2 = datetime.today()
        app.logger.info("Analyzed %d raw comments from %d in %s seconds", parsed_count, len(raw_comments), time2 - time1)

        return "done"

    @has_access
    @expose("/log")
    def parse_log(self):
        return self.get_logs()

class ParseSwiftView(BaseWithLogs):
    route_base = "/parseSwift"

    @has_access
    @expose("", methods=['POST'])
    def parse_with_params(self):
        count = -1  # '-1' means "all".
        if 'count' in request.form:
            count = int(request.form['count'])

        thread = Thread(name="parse_swift", target=ParseSwiftView.parse_swift, args=[self, count])
        thread.start()
        return "parse_swift: count=%d" % count

    def parse_swift(self, count: int):
        self.init_logs_keeper()
        self.progress_stage = 1
        time1 = datetime.today()
        raw_comments = db.session.query(RawComment).limit(count).all()
        parsed_count = 0
        for rc in raw_comments:
            if rc.path[-5:] == 'swift':
                parsed_count += 1
                lines_arr = []
                git_files = parse_git_diff(rc.diff_hunk, rc.path)
                assert len(git_files) == 1, "parse_git_diff returns not 1 GitFile"
                for file in git_files:
                    assert len(file.pieces) == 1, "git file has more than 1 piece"
                    for piece in file.pieces:
                        line_type = piece.lines[len(piece.lines) - 1].type
                        for line in piece.lines:
                            if line.type == GitLineType.UNCHANGED or line.type == line_type:
                                lines_arr.append(line.line if line.line[0] != '+' and line.line[0] != '-' else line.line[1:])
                parser = SwiftParser()
                parsed_results = parser.parse(lines_arr)
                app.logger.info(str(parsed_results[-1:][0]))

        time2 = datetime.today()
        app.logger.info("Analyzed %d raw comments from %d in %s seconds", parsed_count, len(raw_comments), time2 - time1)

        return "done"

    @has_access
    @expose("/log")
    def parse_swift_log(self):
        return self.get_logs()



class TrainView(BaseWithLogs):
    route_base = "/train"

    @has_access
    @expose("", methods=['POST'])
    def analyze_with_params(self):
        steps_count = 100
        if 'steps_count' in request.form:
            steps_count = int(request.form['steps_count'])
        thread = Thread(name="train", target=TrainView.train, args=[self, steps_count])
        thread.start()
        return "train: steps_count=%d" % steps_count

    def train(self, steps_count: int):
        self.init_logs_keeper()
        self.progress_stage = 1
        app.logger.info("START: Train assistant in %d steps.", steps_count)
        rcs_count = db.session.query(RawComment).count()
        time1 = datetime.today()
        train_net(app.logger, rcs_count, steps_count)
        time2 = datetime.today()
        app.logger.info("END: Trained using %d stepss in %s seconds. Code review helper is ready for assist!",
                        steps_count, time2 - time1)
        self.progress_stage = 2
        return "done"

    @has_access
    @expose("/log")
    def analyze_log(self):
        return self.get_logs()


class RawCommentView(ModelView):
    route_base = "/raw_comments"
    datamodel = SQLAInterface(RawComment)
    search_exclude_columns = ["id"]
    page_size = 50
    list_columns = ["message_with_format", "path", "updated_at"]


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
    datamodel = SQLAInterface(PullRequest)
    page_size = 50
    list_columns = ["number", "state", "link"]
    related_views = [RawCommentView]


class PullRequestView(BaseView):  # TODO remove - use from database.
    route_base = "/pr"

    @has_access
    @expose("", methods=['POST'])
    def open_pr(self):
        pr_number = request.form["number"]
        pr: PullRequest = fetch_pr_from_github(app.logger, app.config['ACCOUNTS'][0], app.config['REPO_OWNER'],\
                app.config['REPO'], pr_number)
        lines = str(pr.diff).split('\\n')
        # TODO save PR's data into database (to check results on local data).
        # TODO git_diff = parse_git_diff(pr.diff) and use lines and etc. from this detailed data.
        # Maybe better to parse all pull requests on start for this?
        return render_template("pullrequest.html", base_template = appbuilder.base_template, appbuilder=appbuilder,\
                pr_link=pr.link, pr_number=pr.number, pr_status=pr.state, pr_diff=lines)


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
appbuilder.add_view(RawCommentView, "List fetched comments", category="GitHub data")
appbuilder.add_view(PullRequestsView, "List Pull Requests", category="GitHub data")
appbuilder.add_view_no_menu(PullRequestView)
appbuilder.add_view_no_menu(FetchView)
appbuilder.add_view_no_menu(AnalyzeView)
appbuilder.add_view_no_menu(TrainView)
appbuilder.add_view_no_menu(SiteMapView)
appbuilder.add_view_no_menu(ParseView)
appbuilder.add_view_no_menu(ParseSwiftView)
