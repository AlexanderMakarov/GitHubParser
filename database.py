import sqlite3
from raw_comment import RawComment
from comment import Comment


CREATE_RAW_COMMENTS_DB = """
CREATE TABLE IF NOT EXISTS raw_comments (
 id integer PRIMARY KEY AUTOINCREMENT,
 message text NOT NULL,
 message_with_format text NOT NULL,
 html_url text NOT NULL,
 path text NOT NULL,
 line integer,
 diff_hunk text NOT NULL
);
"""


CREATE_COMMENTS_DB = """
CREATE TABLE IF NOT EXISTS comments (
 id integer PRIMARY KEY AUTOINCREMENT,
 raw_comment_id integer,
 line text NOT NULL,
 git_type integer,
 file_type integer,
 line_type integer
);
"""


def create_connection(db_file: str):
    try:
        conn = sqlite3.connect(db_file)
        return conn
    except Error as e:
        print(e)

    return None


def _db_insert_many(cursor, table_name: str, columns, values):
    column_names = ','.join(columns)
    values_placeholders = ','.join(['?' for x in columns])
    # executemany fails with "sqlite3.InterfaceError: Error binding parameter 0 - probably unsupported type."
    for c in values:
        cursor.execute('INSERT INTO "{0}" ({1}) VALUES ({2})'.format(table_name, column_names, values_placeholders), c)


def raw_comments_to_db(raw_comments: [RawComment], db_file: str):
    conn = create_connection(db_file)
    cursor = conn.cursor()
    cursor.execute(CREATE_RAW_COMMENTS_DB)
    conn.commit()
    columns = ["message", "message_with_format", "html_url", "path", "line", "diff_hunk"]
    values = []
    for c in raw_comments:
        values.append([c.message, c.message_with_format, c.html_url, c.path, c.line, c.diff_hunk])
    _db_insert_many(cursor, "raw_comments", columns, values)
    conn.commit()


def comments_to_db(comments: [Comment], db_file: str):
    conn = create_connection(db_file)
    cursor = conn.cursor()
    cursor.execute(CREATE_COMMENTS_DB)
    conn.commit()
    columns = ["raw_comment_id", "line", "git_type", "file_type", "line_type"]
    values = []
    for c in comments:
        values.append([c.raw_comment.id, c.line, c.git_type, c.file_type, c.line_type])
    _db_insert_many(cursor, "comments", columns, values)
    conn.commit()


def get_raw_comments(db_file: str):
    conn = create_connection(db_file)
    cursor = conn.cursor()
    return cursor.execute("SELECT * FROM raw_comments").fetchall()


def get_comments(db_file: str):
    conn = create_connection(db_file)
    cursor = conn.cursor()
    return cursor.execute("SELECT * FROM comments").fetchall()
