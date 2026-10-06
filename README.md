# OpsReplay

Release and incident intelligence for small engineering teams.

OpsReplay ingests operational events from GitHub and alert webhooks, builds evidence-linked chronological timelines, and helps engineers answer **what changed around a production alert**. Resolved incidents can produce an OpenAI-drafted postmortem grounded in that timeline evidence.

**Live site:** [opsreplay.pages.dev](https://opsreplay.pages.dev/)

**Status:** Active development — FastAPI backend implemented; product UI in progress.

## Why it is interesting

OpsReplay connects production alerts with the releases, merges, and other changes that preceded them, with provenance on every timeline event. This gives investigations an evidence-backed view of what changed before an incident.

## Capabilities

- **Verified webhook ingress** — GitHub (HMAC-SHA256) and alert webhooks accepted with signature checks and durable delivery handling
- **Idempotent async processing** — transactional outbox → SQS (or local SQS-compatible queue) → background workers turn deliveries into timeline events without losing or double-applying work
- **Evidence-linked timelines** — chronological repository events that retain links back to the originating GitHub or alert delivery
- **Investigation context** — lookback / lookahead windows around an alert so related changes are easy to inspect together
- **Incident lifecycle** — create, track, and resolve incidents keyed to an alert trigger
- **Grounded postmortem drafts** — OpenAI structured drafts for resolved incidents, with server-side validation that citations refer to real timeline events in context
- **Local Compose stack** — API, Postgres, optional queue and workers for end-to-end development

## Architecture

```text
GitHub / alert webhooks
        │
        ▼
  Webhook ingress  ──►  durable delivery + transactional outbox
                                 │
                                 ▼
                          message queue (SQS)
                                 │
                                 ▼
                       background processing
                                 │
                                 ▼
                      timeline storage (Postgres)
                                 │
                                 ▼
              FastAPI  ──  timelines, investigation context,
                           incidents, postmortem drafts
```

## Stack

| Area | Technology |
| --- | --- |
| API | Python, FastAPI |
| Data | PostgreSQL, SQLAlchemy |
| Queue | AWS SQS |
| Auth | HMAC webhook verification |
| LLM | OpenAI (grounded postmortem drafts) |
| Run | Docker Compose |
| Website | Astro, TypeScript (Cloudflare Pages) |

## Repository layout

```text
backend/      FastAPI services, workers, migrations
website/      Public landing page (Astro)
compose.yaml  Local multi-service development
```

## Local setup

Prerequisites: Docker / Docker Compose.

```bash
cp .env.example .env
# set Postgres password, webhook secrets; optional OpenAI key / GitHub App credentials

docker compose up --build
```

Interactive API docs (OpenAPI) are available from the running FastAPI service. Optional Compose profiles start a separate webhook ingress process and a local queue with workers for full async processing.

Website (optional):

```bash
cd website && npm ci && npm run dev
```
