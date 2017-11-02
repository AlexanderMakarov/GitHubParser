Create instance/config.py with content

```
ACCOUNTS = [["name", "password"]] # GitHub account, actually works only 1 account/thread.
REPO = "SmartsheetTests"
REPO_OWNER = "akvelon"
ANALYZE_THREADS_COUNT = 4

DEBUG = True
```
Satisfy dependencies using 'requirements.py' (PyCharm installs them automatically).

Run flask app with "run.py".

Use fabmanager (from flask appbuilder) to create admin user. On Windows it will be placed somewhere in "c:\Python36\Scripts\"

Currently only "Fetch <number> raw comments" works on main page. "Raw Comments" and "Comments" works too (with default FAB behavior/style/etc.).
