import threading
import github3
import re
from github3.repos.repo import Repository
from model.raw_comment import RawComment
from logging import Logger
from model.git_data import GitFile, GitLine, GitPiece


def get_repo(username: str, password: str, repo_owner: str, repo_name: str):
    github = github3.login(username, password)
    return github.repository(repo_owner, repo_name)


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


def get_raw_comments_from_github(logger: Logger, accounts: [], repo_name: str, repo_owner: str, count: int = -1):
    tasks = []
    for account in accounts:
        tasks.append(Task(account))

    # Get prs count and all pull requests.
    first_task = tasks[0]
    repo = get_repo(first_task.username, first_task.password, repo_owner, repo_name)

    # We need in count so iterate all at once. Order is reverses here!
    logger.info("Wait about 30 seconds to get data about all closed prs in %s repo, ratelimit_remaining=%d", repo_name,
            repo.ratelimit_remaining)
    prs = list(repo.pull_requests(state="closed", number=count))

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
        thread = threading.Thread(name=task.name, target=parse_raw_comments, args=[task, prs, repo, logger])
        threads.append(thread)
        prs_counter += prs_per_task
        thread.start()
    threads_number = len(threads)
    logger.info("All %d threads started, wait %d seconds", threads_number, prs_per_task * 0.5)
    for thread in threads:
        thread.join()
    result = []
    for task in tasks:
        result.extend(task.result)
    return result


DIFF_DIFF_RE = re.compile("diff --git a/(.+?)( b/)(.*)")


def parse_git_diff_diff_line(line: str):
    """
    diff --git a/iOS/actions/ui/screens/sheet.js b/iOS/actions/ui/screens/sheet.js
    """
    match = DIFF_DIFF_RE.match(line)
    if match and len(match.groups()) == 4:
        return {"a_path": match.group(1), "b_path": match.group(3)}
    return None


DIFF_POSITION_RE = re.compile("@@ -(\d+),(\d+) +(\d+),(\d+) @@ (.*)")


def parse_git_diff_position_line(line: str):
    """
    @@ -278,13 +278,15 @@ Sheet.tapRefresh = function() {
    """
    match = DIFF_POSITION_RE.match(line)
    if match and len(match.groups()) == 4:
        return GitPiece(int(match.group(1)), int(match.group(2)), int(match.group(3)), int(match.group(4)), \
                        match.group(5))
    return None


def parse_git_diff(diff: str):
    """
    Parses "git diff" output into list of 'GitFile' objects.
    """
    if diff.startswith("b'"):
        diff = diff[2:-1]  # Trim "bytestring" format like [b'foo'] -> [foo]
    lines = diff.split('\\n')
    git_lines_counter = 5  # 5: diff, 4: index, 3: ---, 2: +++, 1: @@ (position), 0: regular line of patch.
    piece: GitPiece = None
    index_line = None
    diff_data = None
    pieces = [GitPiece]
    files = [GitFile]
    for i, line in enumerate(lines):

        # Parse lines. Collect data into 'tmp_piece' and 'tmp_diff_data'.
        if git_lines_counter > 0:
            if git_lines_counter == 1:
                tmp_piece = parse_git_diff_position_line(line)
            elif git_lines_counter == 4:
                index_line = line
            elif git_lines_counter == 5:
                tmp_diff_data = parse_git_diff_diff_line(line)
            git_lines_counter -= 1
        else:
            # Try to parse from line "@@" string.
            tmp_piece = parse_git_diff_position_line(line)
            if tmp_piece is None:
                # Try to parse from line "diff" string.
                tmp_diff_data = parse_git_diff_diff_line(line)
                if tmp_diff_data is None:
                    # It is regular line.
                    piece.lines.append(GitLine(line))

        # Combine received data into 'pieces' and 'files'. Set 'tmp_piece'->'piece' and 'tmp_diff_data'->'diff_data'.
        if tmp_piece and len(piece.lines) > 0:  # Check started new piece and previous not empty.
            pieces.append(piece)
            piece = tmp_piece
        if tmp_diff_data:  # Check started new file.
            if piece and len(piece.lines) > 0:  # Add pending piece.
                pieces.append(piece)
            if len(pieces) > 0:  # Check that there are pieces in this file.
                files.append(GitFile(diff_data['b_path'], index_line, pieces))
            diff_data = tmp_diff_data
            git_lines_counter = 4
            index_line = None
    return files


# TODO implement way to store 'PullRequest' or object like this in db. "Diff" should be stored as string.
class PullRequest:
    """
    Pull request to display on site. Not connected to db (at least for now).
    """
    def __init__(self, number: int, link: str, status: str, diff: str):
        self.number = number
        self.link = link
        self.status = status
        self.diff = diff


def fetch_pr_from_github(logger: Logger, account: [], repo_owner: str, repo_name: str, pr_number: int):
    repo: Repository = get_repo(account[0], account[1], repo_owner, repo_name)
    pr = repo.pull_request(pr_number)
    diff: str = pr.diff()
    return PullRequest(pr_number, pr.html_url, pr.state, diff)

