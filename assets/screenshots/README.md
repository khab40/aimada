# AIMADA Publication Screenshot Checklist

Only commit screenshots captured from the real AIMADA application. Do not use fabricated product UI or generic market imagery.

## Required screenshots

| File | UI page/state | Required content | Publication use |
|---|---|---|---|
| `aimada-live-arena.png` | Command Center or Workload Generator, dark mode, bounded scenario active | Order book/liquidity view, scenario state, detector confidence or incident | GitHub social preview, LinkedIn Live Arena image, optional README gallery |
| `aimada-investigation-team.png` | Completed real Nebius-backed Investigation Team result | Specialist findings, consensus, evidence timeline, recommended action, real/Nebius mode indication | GitHub social preview candidate, LinkedIn article, README gallery |
| `aimada-detector-tournament.png` | Completed representative tournament | Serverless Jobs label, completed state, leaderboard, precision/recall/F1, latency, artifacts | GitHub social preview candidate, LinkedIn results section, README gallery |
| `aimada-production-evidence-sync.png` | Execution Trace or Evidence view after S3 sync | Completed Job/Endpoint evidence records, upload/sync status, safe download links | LinkedIn production-evidence section |
| `aimada-architecture.png` | Clean rendered architecture export | Frontend, backend, authoritative runtime, detectors, agents, Endpoint, Jobs, Object Storage/evidence | LinkedIn architecture section |

## Standard capture settings

- Browser viewport: 1920 × 1080
- Zoom: 100%
- Theme: dark
- Format: PNG
- Capture the application content without browser chrome where possible
- Use a deterministic scenario and one representative completed production Job
- Preload all data before recording or capture

## Redaction checklist

Before committing each screenshot, verify that it contains none of the following:

- access-key IDs or secret-access keys;
- bearer tokens, API keys, authorization headers, or JWTs;
- signed S3 URLs;
- private Endpoint hostnames;
- tenant, project, service-account, bucket, or full Job identifiers when sensitive;
- personal email addresses;
- local usernames or home-directory paths;
- unrelated browser tabs, bookmarks, notifications, or account avatars.

Preserve non-sensitive technical proof such as model name, hardware preset, completed status, scenario count, latency, and evaluation metrics.

## Image validation

For every final publication copy:

1. Verify dimensions with an image-inspection tool.
2. Verify the file is readable and not color-profile dependent.
3. Strip EXIF, XMP, editor comments, thumbnails, and unnecessary ICC metadata.
4. Confirm text remains readable at 50% zoom.
5. Run repository secret scanning after the image is committed.
6. Perform a manual visual review; automated secret scanning cannot reliably inspect text rendered inside screenshots.

## README gallery gate

Do not add a README screenshot gallery until these three files are present and reviewed:

- `aimada-live-arena.png`
- `aimada-investigation-team.png`
- `aimada-detector-tournament.png`

When ready, add only a compact three-image gallery with short captions and links to full-resolution files.
