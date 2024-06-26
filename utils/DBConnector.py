from pymongo import MongoClient
from bson.objectid import ObjectId


class DBConnector:
    def __init__(self, DB_HOST, DB_USER=None, DB_PASS=None, DB_CONN_STRING=None):
        # Local MONGO DB
        if DB_USER is not None:
            self.connection = MongoClient(DB_HOST, username=DB_USER, password=DB_PASS)
        else:
            # AZURE CosmosDB RU
            self.connection = MongoClient(DB_HOST)

    def get_db(self, db):
        return self.connection[db]

    def get_document(self, collection, id):
        return collection.find_one(ObjectId(id))


if __name__ == "__main__":
    from dotenv import load_dotenv
    import os
    load_dotenv()

    mongo_db = DBConnector(DB_HOST=os.environ["CA_MONGO_DB_HOST"])
    print(mongo_db.get_db("TestDB"))
