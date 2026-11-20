# Deployment

GitHub Actions builds and deploys separate service images. Backend Dockerfiles
in `api/`, `streaming/`, and `cronjobs/` install dependencies from `uv.lock`
using `uv sync --frozen`. See [deployment and recovery architecture](architecture.md#deployment-and-automatic-recovery)
for the staging deployment path.

## PostgreSQL container version and recovery

Development Compose and CI use `postgres:18`. Keep host-managed staging and
production Compose files on the same major version as their existing database.
Do not use `postgres:latest`: pulling that tag can change the server major version
without upgrading the database files.

For PostgreSQL 18, mount the existing named volume at `/var/lib/postgresql`.
The image uses `/var/lib/postgresql/18/docker` as `PGDATA`. The repository's
Compose file already uses this mount layout. PostgreSQL documents the layout
change in [docker-library/postgres#1259](https://github.com/docker-library/postgres/pull/1259).

Staging uses the bind mount
`/var/www/terminal.binbot.in/pg_data:/var/lib/postgresql`. Keep that mapping;
pin `api_db.image` to `postgres:18` in the host-managed Compose file. Confirm the
cluster version with
`cat /var/www/terminal.binbot.in/pg_data/18/docker/PG_VERSION` and check for a
`PGDATA` override in the host's `.env`. Different hosts can have different cached
images for `postgres:latest`, so production remaining healthy does not establish
that staging is running the same server major version.

If startup reports existing data at `/var/lib/postgresql/18/docker`, inspect the
failing container's server version, `PGDATA`, mounts, and the cluster's
`PG_VERSION` before changing anything. For a confirmed PostgreSQL 18 cluster,
restore `image: postgres:18`, the existing volume mounted at `/var/lib/postgresql`,
and the default `PGDATA` (remove a conflicting override). On a host using this
repository's Compose configuration, apply the fix with:

```sh
docker compose pull api_db
docker compose up -d --no-deps api_db
docker compose ps api_db
docker compose logs --tail=50 api_db
```

These commands recreate the database container while retaining its existing
named volume or bind mount.
Do not remove the volume or use `docker compose down --volumes` / `make down`
during recovery; the current `make down` target removes volumes.

A deliberate major upgrade requires a verified backup and either dump/restore
or `pg_upgrade` with both server versions. Changing the image tag, renaming the
data directory, or editing `PG_VERSION` does not upgrade a cluster. See the
[upstream major-upgrade discussion](https://github.com/docker-library/postgres/issues/37).

## CVD in the streaming worker

The existing streaming service starts CVD collection automatically in the same
Python process. Apply the CVD migration before restarting streaming; no extra
service, image, or Compose profile is required. Allow 30 seconds for graceful
shutdown. See [market CVD operations and protocol](market-cvd.md) for rollout,
retention, ownership, restart and gap semantics.
