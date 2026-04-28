# SignalGraph — implementation progress

## Phase 0 (framing)

- [x] Monorepo layout (`apps/web`, `apps/api`, `packages/*`, `infra/docker`)
- [x] Postgres schema + Alembic initial migration
- [x] Scoring v1 (heuristics, modular weights, raw features + subscores)
- [x] Mock mode for end-to-end UI without GitHub token
- [ ] GH Archive ingestion adapter (deferred; API + mock first)

## Phase 1 (MVP demo)

- [x] FastAPI: `POST /analyze`, repo/timeline/scores/clusters/compare routes
- [x] Next.js: analyze form, repo overview, timeline (Recharts), explanations, peer compare
- [x] Docker Compose (postgres + api + web)
- [ ] Real GitHub stargazer timeline (paginated `star+json`) behind `GITHUB_TOKEN`
- [ ] DuckDB local analytics notebook or CLI (optional)

## Phase 2+

- [ ] Bipartite graph + lockstep prototype (NetworkX)
- [ ] Watchlists, exports, scheduled refresh

## Research links (verify claims in product copy)

- StarScout / ICSE 2026: https://conf.researchr.org/details/icse-2026/icse-2026-research-track/14/Six-Million-Suspected-Fake-Stars-on-GitHub-A-Growing-Spiral-of-Popularity-Contests
- Paper PDF: https://cmustrudel.github.io/papers/icse2026fakestars.pdf
- GitHub stars documentation (interest signal): https://docs.github.com/en/get-started/exploring-projects-on-github/saving-repositories-with-stars
- GH Archive: https://www.gharchive.org/

## Product posture

Use “suspicious,” “elevated manipulation risk,” “coordinated pattern,” “confidence estimate.” Avoid accusatory language; suspected signals can include false positives per research disclaimers.
