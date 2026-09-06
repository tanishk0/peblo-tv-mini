# Peblo TV Mini

## How to run

Copy `.env.example` to `.env`, then start the full stack:

```bash
docker compose up --build
```

Open:

- CMS: `http://localhost:5173/login`
- Viewer: `http://localhost:5174`
- API docs: `http://localhost:8000/docs`

Seeded CMS accounts:

- Admin: `admin@peblo.tv` / `admin123`
- Editor: `editor@peblo.tv` / `editor123`

After startup, log in as the admin, open **Publish**, and publish the seeded catalogue before opening the Viewer.

## Key Decisions & Trade-offs

- **Pre-published catalogue:** The Viewer reads a generated catalogue snapshot instead of querying PostgreSQL directly. This keeps viewer reads simple and fast, at the cost of changes only becoming visible after publishing.
- **Atomic publishing:** Publishing builds and validates a complete new catalogue version before switching the `current` pointer. If publishing fails mid-process, the previous catalogue remains live.
- **Storage abstraction:** Artwork uses a `StorageProvider` interface with local disk for this take-home. Moving to Cloudflare R2 only requires replacing the storage implementation; the API and database model remain unchanged.
- **Backend validation:** Publish-critical validation is enforced server-side so invalid content cannot bypass the UI.
- **Role-based access:** Editors can manage content, while only admins can publish. The Viewer remains unauthenticated and uses only public catalogue endpoints.
- **Language grouping:** Episodes with the same `content_group` are represented as one catalogue entry with available languages.
- **Season 0:** Treated as trailers and excluded from normal Viewer seasons.
- **Search:** Search runs through the API against the published catalogue rather than downloading the entire catalogue to the browser. This is suitable for a small catalogue; at larger scale, indexed PostgreSQL full-text search or a dedicated search engine would be preferable.
- **Local-first deployment:** The application is runnable through Docker Compose rather than deployed to a real cloud environment, since the assessment only requires the deployment step to be documented.
- **Scope & AI:** Optional rollback, publish dry-run, and audit logging were not prioritized in favor of completing and testing the core pipeline. AI coding agents, primarily Codex, were used for implementation and debugging. Generated output was reviewed against the PRD, with changes made where assumptions or UX were incorrect.

## Time spent

Approximately 2 days across backend, CMS, Viewer, testing, and Docker/CI.
