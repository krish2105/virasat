FROM postgis/postgis:16-3.4
# bullseye-security's Release file is expired upstream; the flag keeps the PostGIS 3.4 pin.
RUN apt-get -o Acquire::Check-Valid-Until=false update \
 && apt-get install -y --no-install-recommends postgresql-16-pgvector \
 && rm -rf /var/lib/apt/lists/*
COPY init.sql /docker-entrypoint-initdb.d/10-extensions.sql
