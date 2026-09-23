# OpsReplay Website

The public landing page for [OpsReplay](https://github.com/Tunc0x/opsreplay), a release and incident intelligence tool for small engineering teams.

OpsReplay brings code changes, deployments, alerts, incidents, and other operational events into one chronological timeline so engineers can understand what changed shortly before a production issue occurred.

**Live site:** https://opsreplay.pages.dev/

## Tech stack

- Astro
- TypeScript
- Tailwind CSS
- Lucide icons
- Cloudflare Pages

The site is statically rendered and uses lightweight native TypeScript for its interactive product demonstrations, keeping client-side JavaScript minimal.

## Local development

Requires Node.js 22+ and npm.

```bash
cd website
npm ci
npm run dev
```

The development server runs at:

```text
http://localhost:4173
```

Useful commands:

```bash
npm run check
npm run build
npm run preview
```

Production output is generated in `dist/`.

## Project structure

```text
website/
├── public/                 Static assets and headers
├── src/
│   ├── components/         Shared UI and product-demo components
│   ├── layouts/            Page layout and metadata
│   ├── pages/              Landing page and 404
│   ├── scripts/            Interactive behaviour
│   └── styles/             Global styles and design tokens
├── astro.config.mjs
├── package.json
└── tsconfig.json
```

## Product previews

The incident timeline and postmortem interfaces currently use example data to demonstrate the intended OpsReplay experience.

GitHub integration is under active development. Additional deployment and monitoring integrations, incident workflows, and evidence-grounded postmortem generation are planned as the main application develops.

## Deployment

The site is deployed through Cloudflare Pages from the `website/` directory.

Pushes to `main` automatically trigger a new production deployment.
