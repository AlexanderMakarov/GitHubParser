import os
from flask_appbuilder.security.manager import AUTH_OID, AUTH_REMOTE_USER, AUTH_DB, AUTH_LDAP, AUTH_OAUTH

basedir = os.path.abspath(os.path.dirname(__file__))
SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, "SmartsheetTests3.sqlite")
SQLALCHEMY_TRACK_MODIFICATIONS = False
SECRET_KEY = 'foobar'
AUTH_TYPE = AUTH_DB  # Can't disable auth completely so use internal at least.
AUTH_USER_REGISTRATION = True
# RECAPTCHA_USE_SSL = False
AUTH_USER_REGISTRATION_ROLE = "Admin"
RECAPTCHA_PUBLIC_KEY = '6Ld-NDYUAAAAANOl1A_93iOpuRklYMErx8xApaGH'
RECAPTCHA_PRIVATE_KEY = '6Ld-NDYUAAAAALYTZOJk7XBYHuGDelO3qZV1CjWY'  # I don't pay for it so it is not secret.
#RECAPTCHA_OPTIONS = {'theme': 'white'}
CSRF_ENABLED = True
APP_NAME = "GitHub Review Parser"
APP_THEME = "flatly.css"
