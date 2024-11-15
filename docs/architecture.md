## Database

The new PostgreSQL database introduced a new architecture to the whole API ecosystem. It is based on the [FastAPI full stack template](https://github.com/fastapi/full-stack-fastapi-template).

API layer is now separated from database. On one hand this is to allow the possibility in the future to release staggered API versions that can work independently. E.g. /api/api_v1 /api/api_v2...

On the other hand, the data provided by the Rest API does not have to correspond 1to1 to the data in the Database. At this stage, 2 databases are used, the MongoDB instance serves Big data, that most of the time its unstructure, like candlesticks, because these are indexed by timestamp. However the SQL database is structure data that has matured and is consumed by applications that require performance and a structure.

This separation gives us the flexibility to release API changes independently of what database source we use.
