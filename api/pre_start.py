from api.database.api_db import ApiDb


def pre_start():
    api_db = ApiDb()
    api_db.init_db()

if __name__ == "__main__":
    pre_start()
