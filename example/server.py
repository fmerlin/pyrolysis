from typing import List
import flask
from flask import g
from flask_login import current_user
from flask_sqlalchemy import SQLAlchemy

from models import Item, User, Key
from pyrolysis.server.alchemy import map_dataclasses, transaction
from pyrolysis.server.security import BasicHeader, ApiKeyHeader, JWTHeader
from pyrolysis.server.service import ServerService

flsk = flask.Flask('test')
flsk.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
db = SQLAlchemy(flsk)
map_dataclasses([Item, User, Key])


@flsk.before_first_request
def create_user():
    db.create_all()
    db.session.add(User(id=0, name='myuser', password = 'mypassword', roles=["authenticated"]))
    db.session.add(Key(id=0, key='azerty', roles=["admin"]))
    db.session.commit()


class BasicSecurity(BasicHeader):
    def fetch_roles(self, username, password):
        user = db.session.User.query.filter_by(user=username, password=password).first()
        return user.role if user else []


class ApiKeySecurity(ApiKeyHeader):
    def fetch_roles(self, key):
        key = db.session.Key.query.filter_by(key=key).first()
        return key.role if key else []


class MyJWTSecurity(JWTHeader):
    def fetch_roles(self, token):
        return token.scope


app = ServerService(flsk)
app.register(Item)

basic = BasicSecurity(name='test_sec1')
authenticated = basic.add_role("authenticated")
apikey = ApiKeySecurity(name='test_sec2', header='x-api-key')
admin = apikey.add_role("admin")


@app.get('/items', roles=authenticated and admin)
@transaction(db.session)
def get_all_items() -> List[Item]:
    """
    Example 1 for a unit test

    :return: return data
    """
    return g.session.query(Item).all()


@app.post('/items', roles=authenticated)
@transaction(db.session)
def create_item(e: Item) -> int:
    """
    Example 1 for a unit test

    :param e: example of description
    :return: return data
    """
    e.userid = current_user.id
    return g.session.query(Item).add(e)


@app.get('/items/<p>')
@transaction(db.session)
def get_item(id: int) -> Item:
    """
    Example 1 for a unit test

    :param id: example of description
    :return: return data
    """
    return g.session.query(Item).get(id)


@app.delete('/items/<p>', roles=authenticated)
@transaction(db.session)
def delete_item(id: int) -> int:
    """
    Example 1 for a unit test

    :param id: example of description
    :return: return data
    """
    return g.session.query(Item).delete(id)


@app.put('/items/<p>', roles=authenticated)
@transaction(db.session)
def put_item(e: Item) -> int:
    """
    Example 1 for a unit test

    :param e: example of description
    :return: return data
    """
    return g.session.query(Item).update(e)
