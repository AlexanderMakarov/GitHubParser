from peewee import *


db = None

def initialize(db_file: str):
    db = SqliteDatabase(db_file)
    db.connect()


class BaseModel(Model):
    class Meta:
        database = db