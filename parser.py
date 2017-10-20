#!/usr/bin/env python

# Parses repo. Creds and data in config.py file
#accounts=[["username", "password"]]
#is_analyse=False
#repo="SmartsheetTests"
#repo_owner="akvelon"
#file="SmartsheetTests"

import sys
from datetime import datetime
import threading
import config
import github3
import analyzer
from raw_comment import RawComment
import database

"""
github = github3.login(config.username, config.password)
repo = github.repository(config.repo_owner, config.repo)
count = 0
for issue in repo.pull_requests(state="closed"):
    print('{0}#{1.number}: "{1.title}"\n\t{1.html_url}'.format(repo, issue))
    count += 1
    if count > 10:
        break
print("retelimit=%d" % repo.ratelimit_remaining)
"""


class Task:
    def __init__(self, account):
        self.username = account[0]
        self.password = account[1]
        self.start = 0
        self.end = 0
        self.name = self.username
        self.result = []


def save_in_bd_raw_comments(comments, file_name):
    pass


def get_raw_pr_data(pr_index, repo):
    pr = repo.pull_request(pr_index) # PullRequest class
    counter = 0
    comments = []
    for rc in pr.review_comments():
        counter += 1
        comments.append(RawComment(rc.body_text, rc.body, rc.html_url['href'], rc.path, rc.original_position, rc.diff_hunk))
    return comments


def get_prs(is_analyse, task):
    github = github3.login(task.username, task.password)
    repo = github.repository(config.repo_owner, config.repo)
    for pr_index in range(task.start, task.end):
        raw_comments = get_raw_pr_data(pr_index, repo)
        if is_analyse:
            for raw_comment in raw_comments:
                comment = analyzer.parse(raw_comment)
                #save_in_bd_comment(comment) TODO
                task.result.append(comment)
        else:
            task.result.extend(raw_comments)
    print("%s task done, ratelimit_remaining=%d" % (task.name, repo.ratelimit_remaining))


def get_from_github():
    tasks = []
    for account in config.accounts:
        tasks.append(Task(account))

    # Get prs count and all pull requests.
    first_task = tasks[0]
    github = github3.login(first_task.username, first_task.password)
    repo = github.repository(config.repo_owner, config.repo)
    prs = repo.pull_requests(state="closed")

    print(repo.readme())

    # Calculate count of prs per task. Don't handle cases when unmerged PR's not last.
    prs_count = prs.count
    tasks_count = len(tasks)
    prs_per_task = prs_count // tasks_count
    print("Split %d PRs from %s repo per %d tasks by %d pts" % (prs_count, config.repo, tasks_count, prs_per_task))

    # Split prs by tasks and make threads.
    threads = []
    prs_counter = 1
    for task in tasks:
        task.start = prs_counter
        task.end = prs_counter + prs_per_task
        task.name = "%s[%d..%d]" % (task.username, task.start, task.end)
        thread = threading.Thread(name=task.name, target=get_prs, args=[config.is_analyse, task])
        threads.append(thread)
        prs_counter += prs_per_task
        thread.start()
    threads_number = len(threads)
    estimate = prs_per_task * (10 if config.is_analyse else 0.8) # 10, 2 - correct
    print("All %d threads started, wait %d seconds" % (threads_number, estimate))
    for thread in threads:
        thread.join()
    result = []
    for task in tasks:
        result.extend(task.result)
    return result


# Entry point.
time1 = datetime.today()
comments = get_from_github()
#comments = [RawComment("a", "b", "c", "d", 1, "f"), RawComment("a", "b", "c", "d", 2, "f")]
time2 = datetime.today()
print("Received %d comments for %s" % (len(comments), time2 - time1))
database.raw_comments_to_db(comments, config.db_file)
time3 = datetime.today()
print("Saved %d comments for %s" % (len(comments), time3 - time2))
