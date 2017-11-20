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

"Analyze" shows/saves in db nothing for now. Need to complete.

Most important tasks:

- [ ] Complete Pull Request page. Now for debug, not for code review
- [ ] Implement connection with TensorFlow (load data from sqlite)
- [ ] Complete analyzer (search features in diff_hunk-s and PR patches)
- [ ] Implement **GitHub** Pull Request page (overlay for iframe or other way to do code review with tips from app)
