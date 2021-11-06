# Why no use gevent to improve performance?
Gevent causes maximum depth issues

# Why not centralize app.blueprints in app.py
Circular import issues appear when this is done. That's because `create_app` is used in inheritance

# Tried to solve the Mongodb warning?
Gunicorn uses a prefork model, opening websockets in multiple threads forces us to create MongoClient after it's been forked, so it's unavoidable.

The way to fix this indefinately, would be to websockets as a separate application away from the API. But this is not possible at the moment. It's just a warning anyway, as long as Db consistency is maintaned (different MongoClients update DB correctly) it should be fine.