# Database setup

The warehouse is a PostgreSQL database named `merida_dw` with the PostGIS extension. Two routes
are supported; both end with the same `.env` file. Docker is the recommended one: nothing has to
be installed besides Docker itself, and everyone gets the same PostgreSQL and PostGIS versions.

## Route A — Docker (recommended)

```bash
cp .env.example .env      # set PGPASSWORD first
docker compose up -d
docker compose exec db psql -U postgres -d merida_dw -c "SELECT postgis_full_version();"
```

The `postgis/postgis:17-3.5` image creates the database with PostGIS already enabled. On first
start the container restarts once while it initialises; wait a few seconds if the first
connection is refused.

If port 5432 is already used by a local PostgreSQL, set another port in `.env` (for example
`PGPORT=5434`); `docker compose` publishes the container on that port.

Stop it with `docker compose down`; add `-v` to delete the stored data as well.

## Route B — local PostgreSQL

Requirements: PostgreSQL 15 or newer with the PostGIS bundle installed (on Windows, install it
with Stack Builder: *Spatial Extensions → PostGIS*).

```bash
createdb -U postgres merida_dw
psql -U postgres -d merida_dw -c "CREATE EXTENSION IF NOT EXISTS postgis;"
psql -U postgres -d merida_dw -c "SELECT postgis_full_version();"
```

## Connection settings

Copy `.env.example` to `.env` and set the values. The file is ignored by Git.

| Variable | Meaning | Default |
|---|---|---|
| `PGHOST` | server host | `localhost` |
| `PGPORT` | server port | `5432` |
| `PGDATABASE` | database name | `merida_dw` |
| `PGUSER` | role used by the pipeline | `postgres` |
| `PGPASSWORD` | password of that role | none |

The pipeline creates two schemas: `staging` (cleaned tables as loaded from Python) and `dw`
(dimensions, facts and KPI views). Both are dropped and rebuilt on every load, so the database
can be reused safely.
