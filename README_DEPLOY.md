# CAOS Prototype Linode Deployment Scaffold

This is a **Linode deployment scaffold for the existing Emergent-hosted CAOS prototype**. It is **not production-ready CAOS Care** and it does not claim to remove all Emergent dependencies yet.

CAOS and CAOS Care should remain separate products in the CAOS ecosystem. This scaffold is meant to make the current prototype understandable and runnable in a normal server-shaped environment before later migration tasks replace prototype dependencies.

## What this scaffold adds

- `Dockerfile.backend` for the FastAPI/Uvicorn backend (`backend/server.py`, app object `app`).
- `Dockerfile.frontend` for the React/CRACO frontend build served by nginx.
- `docker-compose.yml` with:
  - `caos-prototype-api`
  - `caos-prototype-web`
  - `caos-prototype-mongo`
  - persistent MongoDB volume
  - persistent uploads volume mounted at `/app/backend/uploads`
- `infra/nginx/caos-prototype.conf` for same-origin `/api` proxying.
- `.env.example` with placeholder-only configuration.
- `scripts/server-inspect.sh` for read-only server inspection.
- `scripts/deploy.sh` for cautious local/Linode compose deployment.

## Prerequisites

On an Ubuntu/Linode VPS or local Linux server:

- Git
- Docker Engine
- Docker Compose plugin (`docker compose`, not necessarily legacy `docker-compose`)
- Enough disk space for Docker images, MongoDB data, and uploads
- A firewall/reverse-proxy plan before exposing this publicly

This scaffold does not install system packages for you.

## First-time setup

Clone the repository and check out the deployment branch:

```bash
git clone <repo-url> /opt/caoscare/prototype
cd /opt/caoscare/prototype
git checkout main
```

If testing this PR before merge, check out the PR head branch shown by GitHub instead of `main`.

Create an environment file from placeholders:

```bash
cp .env.example .env
```

Edit `.env` and replace placeholder values. Do not commit `.env`.

## Environment setup notes

Minimum local scaffold values:

```text
MONGO_URL=mongodb://caos-prototype-mongo:27017
DB_NAME=caos_prototype
CORS_ORIGINS=*
CAOS_PROTOTYPE_WEB_PORT=8080
```

Many prototype features still depend on external providers or Emergent-era integrations. Leave optional placeholders unset only if you understand which features will be unavailable.

Important examples:

- `EMERGENT_LLM_KEY` is still used by the prototype LLM path and Emergent object storage path.
- `CONNECTOR_TOKEN_FERNET_KEY` is required before connector OAuth token storage can work safely.
- `OPENAI_API_KEY` enables the direct OpenAI voice path.
- `GOOGLE_OAUTH_CLIENT_ID` and `GOOGLE_OAUTH_CLIENT_SECRET` are for Google connector OAuth, not the current main app sign-in replacement.

## Build and start

Validate the Compose file:

```bash
docker compose config
```

Build and start services:

```bash
docker compose up -d --build
```

Or use the cautious helper:

```bash
./scripts/deploy.sh
```

Default local frontend URL:

```text
http://localhost:8080
```

The frontend container serves static files and proxies same-origin API requests from `/api` to the backend service on port `8000`.

## Logs

Show all logs:

```bash
docker compose logs -f
```

Show backend logs:

```bash
docker compose logs -f caos-prototype-api
```

Show frontend/nginx logs:

```bash
docker compose logs -f caos-prototype-web
```

Show MongoDB logs:

```bash
docker compose logs -f caos-prototype-mongo
```

## Stop and restart

Stop containers:

```bash
docker compose stop
```

Restart containers:

```bash
docker compose restart
```

Stop and remove containers while keeping named volumes:

```bash
docker compose down
```

Do not remove volumes unless you intend to delete MongoDB data and uploads.

## Backup notes

Persistent data lives in Docker named volumes:

- `caos-prototype-mongo-data` for MongoDB
- `caos-prototype-uploads` for local upload fallback data

Before production use, define a real backup policy. At minimum:

- Schedule MongoDB dumps from the Mongo container.
- Snapshot or export the uploads volume.
- Test restore into a separate environment.
- Store backups outside the VPS.

Example manual MongoDB dump pattern:

```bash
docker compose exec caos-prototype-mongo mongodump --archive=/tmp/caos-prototype.archive
```

Then copy the archive out of the container and store it securely. Do not place dumps containing user data in Git.

## Server inspection helper

Run the read-only inspection helper on a target server:

```bash
./scripts/server-inspect.sh
```

It prints basic OS, Docker, memory, disk, and open-port information without modifying server state.

## Reverse proxy notes

`infra/nginx/caos-prototype.conf` is used inside the frontend container. It intentionally uses:

```text
server_name _;
```

Do not hardcode production domains in this repo-level scaffold. For a real server, use a server-local reverse proxy or deployment overlay that maps the chosen domain to the compose frontend port.

## Known migration blockers for Task 3

This scaffold deliberately does **not** solve these blockers:

1. **Auth replacement** — main sign-in still uses Emergent-managed OAuth/session exchange in the prototype.
2. **LLM replacement** — universal model routing still depends on `EMERGENT_LLM_KEY` and `emergentintegrations` paths.
3. **Object storage replacement** — file storage still prefers Emergent object storage and only falls back to local disk.
4. **Frontend Emergent cleanup** — source files still include Emergent preview/editor assets; the frontend image strips the Emergent runtime script from the built `index.html` for this scaffold only.
5. **Billing replacement** — Stripe checkout still uses the prototype `emergentintegrations` billing helper.
6. **Healthcheck cleanup** — `/api/health` still reports/checks Emergent-era subsystems and should be made provider-aware.

Do not treat this scaffold as a production CAOS Care launch. It is a controlled migration step for understanding and containerizing the current prototype.