# Validation record

Validated locally on 22 September 2026.

- `npm run build`: passed, with zero Astro errors, warnings, or hints.
- `npm run format:check`: passed.
- `npm audit --omit=dev --audit-level=moderate`: zero vulnerabilities at validation time.
- Desktop visually reviewed in the cloud browser; phone and tablet layouts reviewed using same-origin iframe viewports of 320, 390, and 768 CSS pixels (their available content widths were 305, 375, and 753 pixels because of scrollbars).
- Document scroll widths matched the available viewport widths at all three narrow widths and on desktop; no horizontal page overflow.
- Polished the mobile headline spacing, increased mockup label sizes, stacked the evidence panel, and reviewed the mobile report references.
- Verified timeline filters change the visible count and keep the selected evidence in the filtered list; all-events reset restores six events.
- Verified numbered postmortem references select the matching evidence card and update the accessible status.
- Verified mobile menu open/close and Escape handling.
- All fragment links resolve to actual elements; buttons have accessible names. Semantic landmarks, focus styles, a skip link, and reduced-motion CSS are present.
- No application console warnings/errors observed. The cloud browser emitted unrelated extension metadata errors.
- Production output has local CSS, a self-hosted WOFF2 font, and a 2.5 kB JavaScript module (about 1 kB gzipped). No third-party runtime requests, inline scripts, or inline styles are required.
- Production output contains the landing page and custom 404 only. The temporary responsive-review route was removed.
- Cloudflare security/cache headers are included; their delivery must be verified on Cloudflare after deployment.

## Pending external verification

Cloudflare's dashboard presented a persistent security-verification challenge in the cloud browser, including after one reload. The source and production build are ready, but this session has not created a Pages project or verified a live `pages.dev` deployment. Git integration, HTTPS, deployed asset delivery, and deployed desktop/mobile checks remain pending access to the account.

No Lighthouse score is claimed. The performance assessment above is based on the actual static output and local browser inspection. Backend tests were not rerun because this change only adds the independent website directory.
