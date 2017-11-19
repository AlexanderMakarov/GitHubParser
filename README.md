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

Most important tasks:

- [ ] Complete Pull Request page. Now for debug, not for code review (disputable, see last task).
- [ ] Implement connection with TensorFlow (load data from sqlite)
- [ ] Complete analyzer (search features in diff_hunk-s)
- [ ] Implement **GitHub** Pull Request page (overlay for iframe or other way to do code review with tips from app)


TensorBoard:
Create "instance/tflogs" folder.
Create "instance/run_tensorboard.bat" file with content `tensorboard --logdir tflogs`.
Run "instance/run_tensorboard.bat" and wait something like "TensorBoard 0.4.0rc3 at http://localhost:6006".