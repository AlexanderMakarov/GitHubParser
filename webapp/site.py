from flask import Flask, render_template
import os
from datetime import datetime
from github_parser.parser import get_raw_comments_from_github
import model.base_model as base_model
from model.raw_comment import RawComment
from model.comment import Comment
from model.logger import *
import threading


app = Flask("webapp", template_folder='templates')
app.config.from_object('config')
app.config.from_pyfile('../config.py')


@app.route("/")
@app.route("/home")
def home():
    return render_template("index.html")


@app.route("/comment")
def comments():
    pass


@app.route("/comment/<comment_id>")
def comment(comment_id):
    pass


@app.route("/fetch")
def fetch():
    time1 = datetime.today()
    raw_comments = get_raw_comments_from_github()
    time2 = datetime.today()
    log("Received %d raw comments for %s" % (len(raw_comments), time2 - time1))
    base_model.bulk_insert(RawComment, raw_comments)
    time3 = datetime.today()
    log("Saved %d comments for %s" % (len(raw_comments), time3 - time2))


@app.route("/pr")
def prs():
    pass


@app.route("/pr/<pr_id>")
def pr(pr_id):
    pass
