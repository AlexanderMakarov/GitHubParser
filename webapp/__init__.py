import logging
from flask import Flask
from flask_appbuilder import SQLA, AppBuilder
from webapp.index import SiteIndexView


logging.basicConfig(format='%(asctime)s:%(levelname)s:%(name)s:%(message)s')
logging.getLogger().setLevel(logging.DEBUG)

app = Flask(__name__, instance_relative_config=True)
app.config.from_object('config')
app.config.from_pyfile('config.py')
db = SQLA(app, session_options={"autoflush": False})
appbuilder = AppBuilder(app, db.session, indexview=SiteIndexView)


# Line below - entry point into "webapp" folder.
from webapp import views
