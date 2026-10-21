## PR: chore/devops-bootstrap

### Scope
- Adds a reproducible Docker Compose scaffold (FastAPI + Nginx frontend + PostgreSQL).
- Adds role ownership, proposed API contract, `.gitignore` / `.env.example`, smoke tests, GitHub Actions.
- Provides a working placeholder page that calls `/api/v1/health` via Nginx and checks PostgreSQL.

### Validation checklist
- [ ] `cp .env.example .env && docker compose config --quiet`
- [ ] `docker compose up -d --build --wait`
- [ ] `bash tests/smoke.sh`
- [ ] GitHub Actions completed successfully
- [ ] Frontend/Backend/Data/AI owners reviewed contract

### Intentional non-goals / follow-ups
- Frontend is a **temporary static page**, not the final React UI.
- Backend only implements health + empty companies stub; no news or AI logic yet.
- DB schema/migrations, model calls, ingestion, genuine E2E and automated tests are feature PRs.
- Exact frontend/backend dependency lockfiles, image digests and THIRD_PARTY_NOTICES need updating with owners' real dependencies before submission.

### Risk
- Feature developer PRs must rebase onto the bootstrap branch after merge; avoid overwriting existing work in `feat-backend`.
