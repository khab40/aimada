# AIMADA Social Preview Capture Specification

The final social-preview PNG must be created from **real AIMADA application screenshots**. Do not generate or draw substitute product UI.

## Final output

`assets/social/aimada-github-social-preview.png`

- 1280 × 640 px
- PNG
- under 1 MB
- dark graphite/navy background matching AIMADA dark mode

## Source captures required

- `../screenshots/aimada-live-arena.png`
- Either `../screenshots/aimada-investigation-team.png` or `../screenshots/aimada-detector-tournament.png`

## Capture state

### Live Arena source

1. Start the deterministic local or production-backed demo.
2. Allow normal liquidity to form.
3. Launch one bounded spoofing-like or layering-like scenario.
4. Capture a state containing:
   - readable order-book or liquidity visualization;
   - active scenario label;
   - detector confidence or incident indicator;
   - no browser address bar or private URL.

### Secondary panel source

Prefer the Investigation Team when the findings, consensus, timeline, and recommended action fit legibly in one panel. Otherwise use the completed Detector Tournament leaderboard with metrics and artifact links.

## Layout

- Left 58–62%: Live Arena crop.
- Right 38–42%: Investigation Team or Detector Tournament crop.
- Add a dark overlay only as needed for text contrast.
- Title at top left: `AIMADA`.
- Subtitle: `AI Market Abuse Detection Arena`.
- Supporting line near the bottom: `Built with Nebius Serverless AI Jobs + Endpoints`.
- Keep all key content at least 48 px inside the canvas edges.

## Typography

Use the same sans-serif family as the AIMADA UI where available. Keep the hierarchy simple:

- AIMADA: 64–76 px, bold
- Subtitle: 28–34 px
- Supporting line: 20–24 px

Do not add metrics, hashtags, disclaimers, or more than the three required text elements.

## Security review

Hide or redact:

- browser URLs;
- Endpoint hostnames when private;
- bearer tokens and API keys;
- Job, tenant, project, service-account, or bucket identifiers when sensitive;
- signed S3 links;
- personal email addresses and local usernames.

## Export validation

- Confirm dimensions are exactly 1280 × 640.
- Confirm file size is under 1 MB.
- Strip EXIF/XMP/editor metadata.
- Inspect at 50% zoom for text readability.
- Inspect in both light and dark page surroundings.
- Do not commit the PNG until both source captures are real and manually reviewed.
