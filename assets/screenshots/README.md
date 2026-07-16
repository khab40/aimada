# LOB Arena Publication Screenshot Checklist

Only commit screenshots captured from the real LOB Arena application. Do not use fabricated product UI or generic market imagery. The repository keeps one compact, reviewed screenshot per published README state; intermediate captures are intentionally excluded.

## Required screenshots

| File | UI page/state | Required content | Publication use |
|---|---|---|---|
| `Screenshot 2026-07-14 at 19.06.53.png` | Runtime status | Nebius runtime status and safe configuration | README runtime gallery |
| `Screenshot 2026-07-14 at 17.41.43.png` | Investigation Team | Completed investigation output | README investigation gallery |
| `Screenshot 2026-07-14 at 19.07.47.png` | Detector Tournament | Leaderboard and precision/recall/F1 output | README results gallery |
| `Screenshot 2026-07-14 at 19.08.40.png` | Execution Trace | Completed execution and artifact trace | README evidence gallery |

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

Keep the README gallery limited to the four reviewed files listed above. Replace an image only after applying the redaction and validation checklist, and remove superseded intermediate captures rather than accumulating them.
