from flask import render_template
from flask_appbuilder.models.sqla.interface import SQLAInterface
from flask_appbuilder import AppBuilder, ModelView, expose, BaseView, has_access
from webapp import appbuilder, app, db
from datetime import datetime
from github_parser.parser import get_raw_comments_from_github
from model.raw_comment import RawComment
from model.comment import Comment


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

    @expose("/<int:count>")
    @has_access
    def fetch(self, count):
        time1 = datetime.today()
        raw_comments = get_raw_comments_from_github(app.logger, app.config['ACCOUNTS'], app.config['REPO'],
                app.config['REPO_OWNER'], count)
        time2 = datetime.today()
        resulting_count = len(raw_comments)
        app.logger.info("Fetched %d raw comments in %d seconds", resulting_count, int(time2 - time1))
        self.datamodel.session.bulk_save_objects(raw_comments)
        self.datamodel.session.commit()
        app.logger.info("Saved %d raw comments into database", resulting_count)
        return "done"


        # https://docs.python.org/3/library/logging.handlers.html#logging.handlers.MemoryHandler
        """log("Received %d raw comments for %s" % (len(raw_comments), time2 - time1))
        base_model.bulk_insert(RawComment, raw_comments)
        time3 = datetime.today()
        log("Saved %d comments for %s" % (len(raw_comments), time3 - time2))"""



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


db.create_all()
#appbuilder.add_view(HomeView, "Home", category="Home")
appbuilder.add_view(RawCommentView, "List fetched comments", category="Raw Comments")
appbuilder.add_view(CommentView, "List Comments", category="Comments")
appbuilder.add_view(PullRequestsView, "List Pull Requests", category="Pull Requests")
appbuilder.add_view_no_menu(FetchView, "Fetch")