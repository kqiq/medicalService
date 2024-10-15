import dbm
# low latency , overhead internal python persistent key value store.
import json

class Database :
    def __init__(self, db_path='/tmp/xnyb') :
        self.db = dbm.open(db_path , 'c');

    def get(self, key) :
        return json.loads(self.db.get(key.encode()  , b'{}'));

    def set(self ,key, value) :
        self.db[key] = json.dumps(value, ensure_ascii=False);

    def close(self):
        self.db.close();

    def delete(self, key):
        try:
            del self.db[key.encode()]
        except KeyError:
            pass  # Key does not exist, nothing to delete

    def get_all_keys(self):
        return [key.decode() for key in self.db.keys()]
