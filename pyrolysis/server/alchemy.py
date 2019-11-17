import dataclasses
from datetime import datetime, date
from functools import wraps
import sqlalchemy.orm
from flask import g

alchemy_types = {
    str: sqlalchemy.String,
    int: sqlalchemy.Integer,
    float: sqlalchemy.Float,
    datetime: sqlalchemy.DateTime,
    date: sqlalchemy.Date
}


def transaction(session: sqlalchemy.orm.Session):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                g.session = session
                res = func(*args, **kwargs)
                session.commit()
                return res
            except BaseException as e:
                session.rollback()
                raise e
        return wrapper
    return decorator


def map_dataclass_field(field):
    pk = field.metadata.get('primary_key', False)
    comment = field.metadata.get('comment', "")
    if dataclasses.is_dataclass(field.type):
        return sqlalchemy.Column(field.name + '_id', sqlalchemy.Integer)
    return sqlalchemy.Column(field.name, alchemy_types[field.type], primary_key=pk, comment=comment)


def map_dataclass_relationship(field):
    return sqlalchemy.orm.relationship(field.type, ref=field.name + '_id')


def map_dataclasses(classes):
    metadata = sqlalchemy.MetaData()

    for cls in classes:
        cols = [map_dataclass_field(f) for f in dataclasses.fields(cls)]
        props = dict((f.name, map_dataclass_field(f)) for f in dataclasses.fields(cls) if dataclasses.is_dataclass(f.type))
        table = sqlalchemy.Table(cls.__name__, metadata, *cols)
        sqlalchemy.orm.mapper(cls, table, properties=props)
