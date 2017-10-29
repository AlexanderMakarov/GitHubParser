Create instance/config.py with content

```
ACCOUNTS = [["name", "password"]] # GitHub account, actually works only 1 account/thread.
REPO = "SmartsheetTests"
REPO_OWNER = "akvelon"
ANALYZE_THREADS_COUNT = 4

DEBUG = True
```
Run flask app with "run.py".

Use fabmanager (from flask appbuilder) to create admin user.