from peewee import *


db_proxy = Proxy()


def initialize(db_file: str, tables: []):
    db = SqliteDatabase(db_file)
    if db.is_closed():
        db.connect()
    db_proxy.initialize(db)
    db.create_tables(tables, safe=True)
    print("Connected to %s database" % db_file)


def bulk_insert(model: Model, data: [Model]):

    # Model.bulk_insert seems like works only if is specified dictionary, not list of instances.
    with db_proxy.atomic():
        for model in data:
            model.save()


class BaseModel(Model):
    class Meta:
        database = db_proxy
