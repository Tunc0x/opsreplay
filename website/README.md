# OpsReplay website

The public marketing site for [OpsReplay](https://github.com/Tunc0x/opsreplay). A static Astro site with interactive, illustrative incident and postmortem previews.

## Local setup

Requires Node.js 22.12+ (Node 22 LTS recommended) and npm. This directory has its own package manifest and lockfile. It does not use or change the Python application, Docker Compose, or `apps/web`.

```sh
cd website
npm ci
npm run dev
```

The development server listens on port 4173. Open `http://localhost:4173`.

```sh
npm run check   # Strict TypeScript / Astro diagnostics
npm run build   # Check types, then generate the static production site
npm run preview # Serve the production build locally on port 4173
```

The build output is `website/dist`. Do not commit `dist`, `node_modules`, or `.astro`.

## Cloudflare Pages deployment

Use **Pages → Connect to Git**, not Workers or Direct Upload. Connect the existing `Tunc0x/opsreplay` repository, limiting the GitHub authorization to this repository where available.

| Setting                | Value                                                   |
| ---------------------- | ------------------------------------------------------- |
| Plan                   | Free                                                    |
| Production branch      | `main`                                                  |
| Root directory         | `website`                                               |
| Framework preset       | Astro                                                   |
| Build command          | `npm run build`                                         |
| Build output directory | `dist`                                                  |
| Node version           | `22` (via `.node-version`; `NODE_VERSION=22` if needed) |
| Domain                 | Cloudflare's assigned `*.pages.dev` domain              |

Git integration automatically builds and deploys pushes to `main`. Set build watch paths to include `website/**` so backend-only changes do not consume Pages builds. Leave preview branches enabled if you want branch preview deployments.

No Cloudflare adapter, Worker, Function, D1 database, secrets, paid plan, credit card, or external analytics service is required for this static site. Static Pages requests are free and unlimited; the Free plan currently includes 500 builds per month, subject to Cloudflare's limits. Do not enable paid add-ons.

`CF_PAGES_URL` is supplied by Cloudflare and sets the canonical origin automatically. After the production project is created, set the optional public `SITE_URL` build variable to the assigned production origin for a stable canonical URL across branch previews. This is a public URL, not a secret. Do not set a custom domain unless separately authorized.

Security and cache headers are in `public/_headers`. JavaScript is emitted as a separate local asset to work with the restrictive Content Security Policy. Fonts are self-hosted. All public routes work as static files; `404.html` supplies the missing-page response.

### Verify after deployment

- Open the production URL over HTTPS at desktop and mobile widths.
- Confirm all assets load and the browser reports no console errors or CSP violations.
- Test section links, the mobile menu (including Escape), timeline filters, evidence selection, and numbered report references.
- Confirm only `website/` files changed in GitHub and the existing backend files are unchanged.
- Make a small intentional website change when desired and verify Git integration creates a deployment. Never force-push to establish deployment.

Official setup and limits:

- https://developers.cloudflare.com/pages/get-started/git-integration/
- https://developers.cloudflare.com/pages/framework-guides/deploy-an-astro-site/
- https://developers.cloudflare.com/pages/platform/limits/
- https://developers.cloudflare.com/pages/functions/pricing/

## Project structure

```text
website/
  public/                 Favicon, robots.txt, Pages security/cache headers
  src/
    components/           Button, Card, Logo, Timeline, Postmortem
    layouts/Layout.astro  Document shell, metadata, font and style entry
    pages/                Landing page and 404
    scripts/site.ts       Menu, event filtering, evidence selection
    styles/global.css     Design tokens, component styles, responsive rules
  astro.config.mjs        Static output, Tailwind, canonical origin
  package.json
  package-lock.json
  tsconfig.json
```

## Visual system

- Charcoal canvas `#0b0e10`; elevated surfaces `#111619` and `#171c20`.
- Warm off-white `#edf0ef`; muted gray `#9aa4a8`; restrained mint `#b2edca`.
- Self-hosted Inter Variable, with a system monospace stack for timestamps and references.
- 1px low-opacity borders, 7px buttons, 12px cards, subtle green ambient light.
- Amber and soft red are reserved for production signals and incident severity.
- HTML/CSS product visualizations with real text; no screenshots, tracking, stock imagery, or remote assets.
- Short CSS entrance/hover effects with `prefers-reduced-motion` support.

## Implementation choices and product assumptions

The repository was in early development when this page was authored. Existing code provides GitHub App plumbing, signature-verified webhooks, outbox/queue processing, push timeline events, and evidence references. It does not yet implement the complete incident UI, deployment/monitoring integrations, or an LLM postmortem assistant.

Accordingly, demonstrations are prominently marked **Product preview / Example data**, GitHub is **In development**, other integrations are **Upcoming**, and postmortems are **Planned**. There are no claims about customers, uptime, performance, certifications, paid plans, or current production availability. The timeline's fictional 22 September 2026 incident is consistent with its postmortem references. Correlation is explicitly distinguished from confirmed causality.

The primary destinations are the product preview and the actual GitHub repository. There is no invented signup or documentation URL.

Astro statically renders all components. Tailwind is available through its Vite integration; shared CSS tokens and components define the visual system. Lucide icons render as inline SVG. The GitHub links use a generic Git fork icon, not a third-party brand asset. React and Motion are intentionally omitted because three small native TypeScript interactions and CSS transitions cover the entire behavior without shipping a component runtime. All meaningful content is available without JavaScript.

## Optional waitlist: prepared, inactive

No emails are collected and no form, API route, or database is deployed. This keeps the first version static and avoids collecting data before a signup workflow is ready.

A future free-tier implementation can add a Pages Function at `functions/api/waitlist.ts` and a D1 binding scoped to this Pages project. Before enabling it:

1. Verify current Functions/Workers and D1 free limits and keep the account on Free.
2. Add a D1 migration with a unique normalized email column, creation timestamp, and consent version.
3. Validate request size, origin, content type, and email server-side; normalize carefully and use prepared statements.
4. Add a honeypot, request throttling (with bounded storage), and Turnstile if needed; never trust a client-only limit.
5. Use a generic success response for both new and existing addresses; show accessible pending/error/success states.
6. Document purpose, retention, deletion/contact process, and privacy information before collecting addresses.
7. Keep secret bindings server-side. No email provider is necessary to store signups.

This is a documented extension point, not an active or advertised feature.
