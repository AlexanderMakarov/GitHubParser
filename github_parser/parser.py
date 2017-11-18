import threading
import github3
import re
from github3.repos.repo import Repository
from github3.pulls import PullRequest as GitHubPullRequest
from model.raw_comment import RawComment
from logging import Logger
from model.pull_request import PullRequest


def get_repo(username: str, password: str, repo_owner: str, repo_name: str):
    """
    Returns GitHub repository object.
    """
    github = github3.login(username, password)
    return github.repository(repo_owner, repo_name)


def get_pull_requests(logger: Logger, username: str, password: str, repo_name: str, repo_owner: str,\
        count: int = -1):
    """
    Returns repo and list of all pull requests (maybe limited by specifed count) in reversed order.
    """

    # Get prs count and all pull requests.
    repo = get_repo(username, password, repo_owner, repo_name)

    # We need in count so iterate all at once. Order is reverses here!
    required_time = 30 if count < 0 else 0.03 * count  # 0.03 - rough time for one pull request.
    logger.info("Wait about %d seconds to get data about all pull requests in %s repo, ratelimit_remaining=%d", \
            required_time, repo_name, repo.ratelimit_remaining)
    return repo, list(repo.pull_requests(state="all", number=count))


def get_raw_comments_from_pr(pr):
    pr_comments = []
    for rc in pr.review_comments():
        pr_comments.append(RawComment(message=rc.body_text, message_with_format=rc.body, html_url=rc.html_url['href'],\
                path=rc.path, line=rc.original_position, diff_hunk=rc.diff_hunk, updated_at=rc.updated_at))
    return pr_comments


class Task:
    """
    Task for parsing raw comments from pull requests.
    """
    def __init__(self, account):
        self.username = account[0]
        self.password = account[1]
        self.start = 0
        self.end = 0
        self.name = self.username
        self.result = []


def parse_raw_comments(task: Task, prs: [], repo, logger: Logger):
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
            logger.info("%s: %d/%d, ratelimit_remaining=%d", task.name, (pr_index - task.start),
                    (task.end - task.start), repo.ratelimit_remaining)
    logger.info("%s task done, ratelimit_remaining=%d", task.name, repo.ratelimit_remaining)


def parse_pull_requests(task: Task, prs: [], repo, logger: Logger):
    # TODO support few accounts in real!
    #github = github3.login(task.username, task.password)
    #repo = github.repository(config.repo_owner, config.repo)
    for pr_index in range(task.start, task.end):
        if pr_index >= len(prs):  # Avoid IndexError for last PR.
            break
        pr = prs[pr_index]
        raw_comments = get_raw_comments_from_pr(pr)
        # Add all PR's even without comments, because AI should train on "no comments" data also.
        result = PullRequest(number=pr.number, link=pr.html_url, state=pr.state, diff=pr.diff(),\
                raw_comments=raw_comments)
        task.result.append(result)
        if (pr_index - task.start) % 10 == 0:  # Log progress every 10 prs.
            logger.info("%s: %d/%d, ratelimit_remaining=%d", task.name, (pr_index - task.start),
                    (task.end - task.start), repo.ratelimit_remaining)
    logger.info("%s task done, ratelimit_remaining=%d", task.name, repo.ratelimit_remaining)


def get_pull_requests_from_github(logger: Logger, accounts: [], repo_name: str, repo_owner: str, count: int = -1):
    """
    Returns list of PullRequests and RawComment-s from GitHub.
    """
    tasks = []
    for account in accounts:
        tasks.append(Task(account))

    # Get prs count and all pull requests.
    first_task = tasks[0]
    repo, prs = get_pull_requests(logger, first_task.username, first_task.password, repo_name, repo_owner, count)

    # Calculate count of prs per task.
    prs_count = len(prs)
    tasks_count = len(tasks)
    prs_per_task = prs_count // tasks_count
    logger.info("Split %d PRs from %s repo per %d task(s) by %d pts, ratelimit_remaining=%d", prs_count,
            repo_name, tasks_count, prs_per_task, repo.ratelimit_remaining)

    # Split prs by tasks and make threads.
    threads = []
    prs_counter = 1
    for task in tasks:
        task.start = prs_counter
        task.end = prs_counter + prs_per_task
        task.name = "%s[%d..%d]" % (task.username, task.start, task.end)
        # target can be also 'parse_raw_comments'.
        thread = threading.Thread(name=task.name, target=parse_pull_requests, args=[task, prs, repo, logger])
        threads.append(thread)
        prs_counter += prs_per_task
        thread.start()
    threads_number = len(threads)
    required_time = 1.12 * prs_per_task  # 1.12 - rough time for one pull request.
    logger.info("All %d threads started, wait %d seconds", threads_number, required_time)
    for thread in threads:
        thread.join()
    result = []
    for task in tasks:
        result.extend(task.result)
    return result


def fetch_pr_from_github(logger: Logger, account: [], repo_owner: str, repo_name: str, pr_number: int):
    repo: Repository = get_repo(account[0], account[1], repo_owner, repo_name)
    pr: github3.pulls.PullRequest = repo.pull_request(pr_number)
    diff: str = pr.diff()
    return PullRequest(number=pr_number, link=pr.html_url, state=pr.state, diff=diff)
