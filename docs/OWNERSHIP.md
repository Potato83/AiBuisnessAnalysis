# Module ownership and branch policy

Team has five roles. GitHub usernames must be confirmed by the TeamLead before assigning CODEOWNERS/reviewers; no usernames are invented here.

| Module | Primary owner | Required reviewer | Branch suggestion |
|---|---|---|---|
| `frontend/` | Frontend developer | Backend developer (API integration) | `feat/frontend` |
| `backend/` | Backend developer | AI or Data developer depending on endpoint | Existing `feat-backend` |
| `data/` + DB schema/migrations | Data/DB developer | Backend developer | `feat/data` |
| `ai/` + prompt/agent orchestration | AI developer | Backend developer | `feat/ai` |
| `docker-compose.yml`, `.github/`, `infra/`, docs/bootstrap | TeamLead / DevOps | Backend developer | `chore/devops-bootstrap` |

## PR rules

- No direct pushes to `main` (enable branch protection in repository settings).
- Branch from `main`; one feature/fix per PR; request one non-author review.
- `docker compose config` and Compose smoke tests must pass before merge.
- Avoid secrets and real company/individual data in git. Use synthetic provided fixtures.
- Record changes to API response shapes in `docs/API_CONTRACT.md` and update frontend contract tests.
- Do not merge feature branches until bootstrap PR is integrated or rebased into the branch.

## Definition of Done for today's bootstrap

- [x] Role ownership and proposed API contract documented
- [x] `.gitignore`, `.env.example`, Docker Compose, Dockerfiles, CI configured
- [x] Minimal API is reachable from frontend at `/api/v1/health` when stack runs
- [ ] Teammates confirm ownership and each creates/pushes feature branch
- [ ] GitHub Actions completes green and a developer confirms local `docker compose up --build`
- [ ] Review first feature PRs together
