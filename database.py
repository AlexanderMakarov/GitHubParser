import sqlite3


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


def create_connection(db_file):
    try:
        conn = sqlite3.connect(db_file)
        return conn
    except Error as e:
        print(e)

    return None


def _db_insert_many(cursor, table_name, columns, values):
    column_names = ','.join(columns)
    values_placeholders = ','.join(['?' for x in columns])
    # executemany fails with "sqlite3.InterfaceError: Error binding parameter 0 - probably unsupported type."
    for c in values:
        cursor.execute('INSERT INTO "{0}" ({1}) VALUES ({2})'.format(table_name, column_names, values_placeholders), c)


def raw_comments_to_db(comments, db_file):
    conn = create_connection(db_file)
    cursor = conn.cursor()
    cursor.execute(CREATE_RAW_COMMENTS_DB)
    conn.commit()
    columns = ["message", "message_with_format", "html_url", "path", "line", "diff_hunk"]
    values = []
    for c in comments:
        values.append([c.message, c.message_with_format, c.html_url, c.path, c.line, c.diff_hunk])
    _db_insert_many(cursor, "raw_comments", columns, values)
    conn.commit()