#!/usr/bin/env python

# Parses repo. Python 3 only! One account GitHub API limits allow parse about 4700 pull requests.
# Creds and data in config.py file:
#accounts=[["username", "password"], ...]
#is_parse=False
#is_analyse=True
#repo="SmartsheetTests"
#repo_owner="akvelon"
#db_file="SmartsheetTests.sqlite"
#analyze_threads_count=4

from datetime import datetime
import threading
import github3
import config
import analyzer
import base_model
from raw_comment import RawComment
from comment import Comment


class Task:
    def __init__(self, account):
        self.username = account[0]
        self.password = account[1]
        self.start = 0
        self.end = 0
        self.name = self.username
        self.result = []


def get_raw_comments_from_pr(pr):
    pr_comments = []
    for rc in pr.review_comments():
        pr_comments.append(RawComment(message=rc.body_text, message_with_format=rc.body, html_url=rc.html_url['href'],
                path=rc.path, line=rc.original_position, diff_hunk=rc.diff_hunk))
    return pr_comments


def parse_raw_comments(task, prs, repo):  # if is_analyse=False then task.result is [RawComment], else [Comment]
    # TODO support few accounts in real!
    #github = github3.login(task.username, task.password)
    #repo = github.repository(config.repo_owner, config.repo)
    for pr_index in range(task.start, task.end):
        if pr_index >= len(prs):  # Avoid IndexError for last PR.
            break
        pr = prs[pr_index]
        raw_comments = get_raw_comments_from_pr(pr)
        task.result.extend(raw_comments)
        if (pr_index - task.start) % 10 == 0:  # Log progress every 10 prs.
            print("%s: %d/%d ratelimit_remaining=%d" % (task.name, (pr_index - task.start), (task.end - task.start),
                    repo.ratelimit_remaining))
    print("%s task done, ratelimit_remaining=%d" % (task.name, repo.ratelimit_remaining))


def get_raw_comments_from_github():
    tasks = []
    for account in config.accounts:
        tasks.append(Task(account))

    # Get prs count and all pull requests.
    first_task = tasks[0]
    github = github3.login(first_task.username, first_task.password)
    repo = github.repository(config.repo_owner, config.repo)
    print("Wait about 30 seconds to get data about all closed prs in %s repo" % config.repo)
    prs = list(repo.pull_requests(state="closed"))  # We need in count so iterate all at once. Order is reverses here!

    # Calculate count of prs per task.
    prs_count = len(prs)
    print("prs_count=" + str(prs_count) + ", ratelimit_remaining=" + str(repo.ratelimit_remaining))
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
        thread = threading.Thread(name=task.name, target=parse_raw_comments, args=[task, prs, repo])
        threads.append(thread)
        prs_counter += prs_per_task
        thread.start()
    threads_number = len(threads)
    estimate = prs_per_task * (1.0 if config.is_analyse else 0.5)  # 0.5 - actually 0.3, 1.0 TODO: 1.0 - correct
    print("All %d threads started, wait %d seconds" % (threads_number, estimate))
    for thread in threads:
        thread.join()
    result = []
    for task in tasks:
        result.extend(task.result)
    return result


# Entry point. Initialize db.
base_model.initialize(config.db_file, [RawComment, Comment])

# Get RawComment-s.
raw_comments = []
if config.is_parse:
    time1 = datetime.today()
    raw_comments = get_raw_comments_from_github()
    time2 = datetime.today()
    print("Received %d raw comments for %s" % (len(raw_comments), time2 - time1))
    base_model.bulk_insert(RawComment, raw_comments)
    (x.save() for x in raw_comments)
    time3 = datetime.today()
    print("Saved %d comments for %s" % (len(raw_comments), time3 - time2))
else:
    raw_comments = [x for x in RawComment.select()]

# Get Comment-s.
comments = []
if config.is_analyse:
    time1 = datetime.today()
    comments = analyzer.analyze_raw_comments(raw_comments, config.analyze_threads_count)
    Comment.delete().execute()
    base_model.bulk_insert(Comment, comments)
    time2 = datetime.today()
    print("Analyzed %d comments for %s" % (len(comments), time2 - time1))
else:
    comments = Comment.select()