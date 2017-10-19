#!/usr/bin/python

# Parses repo. Creds and data in config.properties file
# username=<GitHub account name>
# password=<GitHub account password>
# repo=<GitHub repo to parse name>
# file=<file name to parse dat into>

import sys
import config
import github3


github = github3.login(config.username, config.password)
repo = github.repository(config.repo_owner, config.repo)
count = 0
for issue in repo.pull_requests(state="closed"):
    print('{0}#{1.number}: "{1.title}"\n\t{1.html_url}'.format(repo, issue))
    count += 1
    if count > 10:
        break
print("retelimit=%d" % repo.ratelimit_remaining)