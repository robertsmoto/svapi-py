from __future__ import annotations
from dataclasses import dataclass
import json
from typing import Protocol

class ApiData(Protocol):

    @classmethod
    def read_json(cls, json_str: str) -> ApiData:
        ...

    @classmethod
    def write_json(cls) -> str:
        ...

@dataclass
class OSB():
    ID: str = ''
    schemaVersion: int = 0
    createdAt: str = ''
    updatedAt: str = ''

    @classmethod
    def read_json(cls, json_str: str):
        json_dict = json.loads(json_str)
        for key in json_dict:
            if not hasattr(cls, key):
                print("Object does not have this key", key)
                continue
            setattr(cls, key, json_dict[key])
        return cls

    @classmethod
    def write_json(cls) -> str:
        return json.dumps(cls)

@dataclass
class Article(OSB):
    title: str = ''
    excerpt: str = ''
    body: str = ''
    footer: str = ''

    @classmethod
    def read_json(cls, json_str: str):
        return super().read_json(json_str)

    @classmethod
    def write_json(cls) -> str:
        return super().write_json()

@dataclass
class Collection(OSB):
    name: str = ''
    reverseCollection: bool = False
    sortDocumentsBy: str = ''
    # slug: str = ''
    # menuOrder: Dict = field(default_factory=lambda: {}) 

    @classmethod
    def read_json(cls, json_str: str):
        return super().read_json(json_str)

    @classmethod
    def write_json(cls) -> str:
        return super().write_json()

@dataclass
class CollectionSet(OSB):
    name: str = ''
    reverseCollection: bool = False
    sortDocumentsBy: str = ''
    # menuOrder: Dict = field(default_factory=lambda: {}) 

    @classmethod
    def read_json(cls, json_str: str):
        return super().read_json(json_str)

    @classmethod
    def write_json(cls) -> str:
        return super().write_json()

@dataclass
class Doc(OSB):
    title: str = ''
    excerpt: str = ''
    body: str = ''
    footer: str = ''

    @classmethod
    def read_json(cls, json_str: str):
        return super().read_json(json_str)

    @classmethod
    def write_json(cls) -> str:
        return super().write_json()

@dataclass
class Page(OSB):
    title: str = ''
    excerpt: str = ''
    body: str = ''
    footer: str = ''

    @classmethod
    def read_json(cls, json_str: str):
        return super().read_json(json_str)

    @classmethod
    def write_json(cls) -> str:
        return super().write_json()
