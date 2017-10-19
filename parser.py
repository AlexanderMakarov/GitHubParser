#!/usr/bin/env python

# Parses repo. Creds and data in config.properties file
# username=<GitHub account name>
# password=<GitHub account password>
# repo=<GitHub repo to parse name>
# file=<file name to parse dat into>

import sys
import threading
import config
import github3
import analyzer


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
def parse_task(prefix):
    pass


def save_in_bd(comment):
    pass


def parse(task):
    github = github3.login(task.username, task.password)
    repo = github.repository(config.repo_owner, config.repo)
    for i in range(task.from, task.to):
        pr = repo.pull_request(i)
        comment = analyzer.parse(pr)
        save_in_bd(comment)
    print("%s done" % task.name)


threads = []
config_prefixes = config.accounts.split(',')
for prefix in config_prefixes:
    account = parse_task(prefix)
    thread = Thread(prefix, parse, task)
number = len(threads)
print("All %d threads gone, wait %d minutes" % (number, number * MAGIC))
"""