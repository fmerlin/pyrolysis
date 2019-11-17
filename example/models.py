from dataclasses import dataclass, field
from typing import List


@dataclass
class User:
    id: int = field(metadata=dict(primary_key=True))
    name: str = field()
    password: str = field()
    roles: List[str] = field()


@dataclass
class Key:
    id: int = field(metadata=dict(primary_key=True))
    key: str = field()
    roles: List[str] = field()



@dataclass
class Item:
    id: int = field(metadata=dict(primary_key=True))
    name: str = field()
    user: User = field()
