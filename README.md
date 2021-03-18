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

TensorBoard:
Create "instance/tflogs" folder.
Create "instance/run_tensorboard.bat" file with content `tensorboard --logdir tflogs`.
Run "instance/run_tensorboard.bat" and wait something like "TensorBoard 0.4.0rc3 at http://localhost:6006".


Most important tasks:

- [ ] Improve features saving structure. Predict features count and order. Use numpy arrays for performance.
- [ ] Increase features parsing time. Use paralleling on threads. Append datd to CSV files if possible.
- [ ] Add ability to save and teach net with features based on enums (set of words).
- [ ] Implement **GitHub** Pull Request page (overlay for iframe or other way to do code review with tips from app).

"Analyze" shows/saves in db nothing for now. Need to complete.

Most important tasks (hackaton objectives):

- [ ] Complete Pull Request page. Now for debug, not for code review
- [ ] Implement connection with TensorFlow (load data from sqlite)
- [ ] Complete analyzer (search features in diff_hunk-s and PR patches)
- [ ] Implement **GitHub** Pull Request page (overlay for iframe or other way to do code review with tips from app)
