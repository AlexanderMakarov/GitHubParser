import threading
from raw_comment import RawComment
from comment import Comment


def analyze_raw_comment(rc: RawComment):
    hunk_lines = rc.diff_hunk.split("\n")  # TODO
    rc.comment = Comment(raw_comment=rc, line=hunk_lines[:-1], file_type=0, line_type=0, git_type=0)


def analyze_raw_comments(thread_name: str, raw_comments: [RawComment]):
    for rc in raw_comments:
        analyze_raw_comment(rc)
    print("%s thread done, %d analyzed" % (thread_name, len(raw_comments)))


def analyze_raw_comments(raw_comments: [RawComment], threads_number: int):

    # Calculate count of comments per thread.
    rcs_count = len(raw_comments)
    rcs_per_thread = rcs_count // threads_number
    print("Analyze %d raw comments in %d threads by %d pts" % (rcs_count, threads_number, rcs_per_thread))

    # Split rcs by threads and start.
    threads = []
    for index in range(threads_number):
        start = index * rcs_per_thread
        end = min(start + rcs_per_thread, len(raw_comments))
        thread_name = "%s[%d..%d]" % (index + 1, start, end)
        thread_rcs = raw_comments[start:end]
        thread = threading.Thread(name=thread_name, target=analyze_raw_comments, args=[thread_name, thread_rcs])
        threads.append(thread)
        thread.start()
    threads_number = len(threads)
    estimate = rcs_per_thread * 0.1  # TODO: 0.1 - correct
    print("All %d threads started, wait %d seconds" % (threads_number, estimate))

    # Wait threads done.
    for thread in threads:
        thread.join()
    result = []
    for rc in raw_comments:
        result.append(rc.comment)
    return result