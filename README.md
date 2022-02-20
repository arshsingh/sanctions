## Sanctions Check API

Collects sanctions data from various sources and exposes them through a unified API.

Currently the following sources are used:
- UN Security Council Sanctions
- EU Financial Sanctions File
- U.S. OFAC Specially Designated Nationals

Only basic fields (full names/aliases, timestamp, type etc.) are stored in the DB right now, even though
the sources have more data available. If you'd like to add some more fields (or another source), feel free to open an
issue or send a PR!

#### Development

Assuming docker and docker-compose is installed:
```sh
git clone github.com/arshsingh/sanctions
cd sanctions

cp env.def .env

make run
```

To import some test data:
```sh
make test-data
```

Check `Makefile` for more commands (for e.g. generating migrations)
