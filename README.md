# AiBuisnessAnalysis — Alfa Hack 2026

Prototype for **personalized business news insights**. Project aims to relate news and Alfa-Bank analysis to synthetic company context and make evidence-backed risk/opportunity interpretations. The current `chore/devops-bootstrap` is an **infrastructure scaffold**, not a finished agent or news product.

## Quick start — Docker Compose

Requires Docker Engine with `docker compose` plugin. Clone repo, then:

```sh
cp .env.example .env
# Optional: edit POSTGRES_PASSWORD in .env for local use

docker compose up --build
```

Open `http://localhost:8080/`. The staging page fetches `GET /api/v1/health` through Nginx; backend checks PostgreSQL using `SELECT 1`. No ports are published for API or database. Frontend binds **127.0.0.1:8080** on the Docker host.

Smoke test in another terminal:

```sh
bash tests/smoke.sh
docker compose ps
```

Stop: `docker compose down` (keeps DB volume). Reset all **local** test DB data only if intended: `docker compose down -v`.

## Ubuntu staging VM (alpha-staging)

The team's shared Docker host is an isolated Ubuntu VM behind Alpine `mozzarella`, reachable via VPN and SSH jump. From a laptop with WireGuard and authorized SSH key:

```sh
ssh -J mossad@10.69.67.1 -L 8080:127.0.0.1:8080 devops@192.168.122.178
```

Run Compose *inside the VM* (in a separate VM terminal). Browse `http://127.0.0.1:8080/` **on the laptop** through the SSH tunnel. The VM's DHCP IP may change; validate it with `virsh net-dhcp-leases default` on the Alpine host. Don't expose Portainer, DB, or Docker socket to the internet.

## Services

| Service | Purpose |
|---|---|
| `frontend` | Temporary static Nginx page, reverse proxy to `/api/` (React developer replaces it) |
| `backend` | FastAPI bootstrap routes and DB health probe (Backend developer extends it) |
| `postgres` | PostgreSQL 16 persistent local volume (Data developer adds schema/migrations) |

API proposal: [`docs/API_CONTRACT.md`](docs/API_CONTRACT.md). Roles & PR policy: [`docs/OWNERSHIP.md`](docs/OWNERSHIP.md).

## Developer handoff

Frontend developer: replace static page with React/Vite and multi-stage Dockerfile; commit `package-lock.json` and switch to `npm ci`. Backend developer: implement business endpoints, add tests and dependency lock. Data developer: add synthetic fixture import and schema migrations. AI developer: implement explicit agent steps, evidence trace, and **only case-permitted models**. DevOps: maintain Compose, CI, secrets, hosting.

Project specification also requires source attribution, bank-vs-AI distinction, self-check, third-party notices, and end-to-end demo with synthetic data. None of those AI business features are claimed complete in this bootstrap PR.

## CI

`.github/workflows/ci.yml` runs on pull requests to `main`: validates Compose, builds services, waits for healthchecks, tests browser-facing `/` and `/api/v1/*` routes, and cleans up temporary volumes.

## Security & operations

- `.env` is ignored; `.env.example` contains only a **local** demonstration password. Use per-environment secrets and strong DB passwords outside local development.
- Never mount Docker socket inside application services.
- Keep staging accessible through WireGuard/SSH, not an open PostgreSQL port.
- Do not mistake the empty company list for delivered company-analysis functionality.
- For final hackathon submission, pin image digests and supply lock files + THIRD_PARTY_NOTICES with actual licenses/dependencies from implemented modules.
