from pymongo import MongoClient

from app.settings import settings


def get_db():
    client = MongoClient(settings.mongo_uri)
    return client[settings.mongo_db]

