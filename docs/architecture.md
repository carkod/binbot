## Database

The new PostgreSQL database introduced a new architecture to the whole API ecosystem. It is based on the [FastAPI full stack template](https://github.com/fastapi/full-stack-fastapi-template).

API layer is now separated from database. On one hand this is to allow the possibility in the future to release staggered API versions that can work independently. E.g. /api/api_v1 /api/api_v2...

On the other hand, the data provided by the Rest API does not have to correspond 1to1 to the data in the Database. At this stage, 2 databases are used, the MongoDB instance serves Big data, that most of the time its unstructure, like candlesticks, because these are indexed by timestamp. However the SQL database is structure data that has matured and is consumed by applications that require performance and a structure.

This separation gives us the flexibility to release API changes independently of what database source we use.

| Rest API folder      | Current DB | Status                                            |
|----------------------|------------|---------------------------------------------------|
| Bots                 | Postgres   | Migrated                                          |
| Users                | Postgres   | Migrated                                          |
| Deals                | Postgres   | Migrated (part of Bots)                           |
| Charts               | MongoDB    | Not to be migrated                                |
| Paper trading        | MongoDB    | To be migrated to Postgres                        |
| Autotrade            | MongoDB    | To be migrated to Postgres (settings data)        |
| Research             | MongoDB    | To be migrated to Postgres (renamed to Blacklist) |
| Account              | MongoDB    | To be migrated to Postgres (new table Balances)   |
| three_commas_signals | MongoDB    | 3Commas legacy, kept for reference                |
| subscribed_symbols   | MongoDB    | 3Commas legacy, kept for reference                |

PostgreSQL database is meant to be used for relational data for fast performance. Small chucks of data are consumed rapidly, bots, autotrade settings, users, these is data that can live in independently and are queried in small amounts and punctually.

MongoDB database is meant to be used for time series data (charts) and cache. This is often unstructure data, high volume, high frequency of querying.

Reasons for moving to SQL:
- Better data consistency. Because Document-based NoSQL data is often not strictly typed, the ORM/ODM has fewer guards, and the DB doesn't actually card specifici fields, moving to SQL allows us to better guard such fields. Wrongly or inconsistenly submitted fields in SQL will throw errors and allow us to rollback changes.
- Maturity of Binbot data. As binbot data structure (autotrade settings, bots) become more mature, it's clear to see the relation between the data.
- Future-proof. As project grows, more data related to bots and trades will be added, and we probably don't want to attach it into the exisiting objects that are already very large (bots in MongoDB). This allows us to separate and break down into small chunks and still keep the relationship in the data, e.g. querying all orders without all the overhead of bots.
