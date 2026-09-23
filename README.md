# OpsReplay

OpsReplay is a release and incident intelligence tool for small engineering teams.

It brings software-development and production activity into one chronological timeline, including:

- GitHub pull requests and code changes
- deployments and releases
- production incidents
- errors and alerts
- other operational events

The goal is to make it easier to understand **what changed shortly before something broke in production**.

After an incident, OpsReplay can also generate a draft postmortem grounded in the collected incident evidence, with references back to the underlying timeline events.

## Landing page

🌐 https://opsreplay.pages.dev/

## Current stack

- Python / FastAPI
- TypeScript / React
- PostgreSQL
- AWS / SQS
- Docker
- Terraform
- GitHub Actions
- GitHub App + webhook ingestion

The public landing page is built separately with Astro and deployed via Cloudflare Pages.

## Status

OpsReplay is currently under active development.

Implemented work includes core backend infrastructure, GitHub App integration, webhook ingestion, event processing, and the first public product website.

More integrations, incident workflows, and evidence-backed postmortem generation are being developed incrementally.

## Repository

The main application code and landing page live in this repository.

```text
apps/       Application services
website/    Public OpsReplay landing page