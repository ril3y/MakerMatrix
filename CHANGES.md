# PDF / Datasheet blob-fetch migration (fix/pdf-blob-fetch, uncommitted)

## Context

PR #2 added an auth gate to `GET /api/utility/static/datasheets/{filename}` (and
`GET /api/utility/get_image/{image_id}`). Browsers do not send the Bearer
token when loading `<iframe src>`, `<a href download>`, or `window.open(...)`,
so any production consumer using those tags directly will now 401.

This branch migrates the remaining datasheet consumers in the frontend to the
same authenticated blob-fetch pattern that `PartImage.tsx` already uses for
images.

## What changed

### New helper

- `MakerMatrix/frontend/src/services/datasheet.service.ts` —
  `fetchDatasheetBlob(filename)` and `revokeDatasheetBlob(url)`. Wraps
  `apiClient.get(url, { responseType: 'blob' })` and `URL.createObjectURL` so
  the call sites stay tiny and consistent.

### Component migrations

- `MakerMatrix/frontend/src/components/parts/PartPDFViewer.tsx`
  - Replaced raw `<iframe src="/static/datasheets/...">` with an auth-fetched
    `blob:` URL. Loading/error states and proper cleanup of the object URL on
    close, datasheet swap, and unmount.
  - "Download" and "Open in new tab" buttons reuse the same blob URL, so they
    work without re-fetching and without needing the browser to attach a
    Bearer token.
- `MakerMatrix/frontend/src/pages/parts/PartDetailsPage.tsx`
  - `downloadDatasheet(datasheet)` (uploaded-datasheet card) now fetches the
    bytes via `fetchDatasheetBlob` before triggering the `<a download>`
    click, with the object URL revoked on a 1s timeout.
  - The "Downloaded Datasheet" enriched-card download button (which previously
    built its own `<a href={getDatasheetUrl()} download>`) does the same.
  - Added `getErrorMessage` import for consistent toast formatting on failure.

### Not in scope (intentionally left alone)

- The "Open in new tab" anchor in the "Supplier Datasheet (online)" card
  targets `/api/utility/static/proxy-pdf?url=...` (external-URL proxy with its
  own auth concerns), not `/static/datasheets/`, so it is unaffected by the
  CVE-002 change addressed here.
- `MakerMatrix/frontend/src/components/ui/PDFViewer.tsx` already auth-fetches
  via a raw `fetch(url, { Authorization })`. Functionally safe under the new
  auth gate; left as-is.

## Tests added

- `MakerMatrix/frontend/src/services/__tests__/datasheet.service.test.ts` — 5 cases
  - Requests the correct URL with `responseType: 'blob'`.
  - URL-encodes filenames containing special characters.
  - Propagates errors from `apiClient` (with `getErrorMessage` round-trip).
  - `revokeDatasheetBlob` revokes `blob:` URLs and is a no-op for everything else.
- `MakerMatrix/frontend/src/components/parts/__tests__/PartPDFViewer.test.tsx` — 4 cases
  - No fetch while `isOpen=false`.
  - Fetch is issued and the iframe `src` is the resulting `blob:` URL.
  - `URL.revokeObjectURL` is called on unmount.
  - Error state renders (and no iframe is mounted) when the fetch fails.

## Verification

```bash
cd MakerMatrix/frontend
npm ci                  # this is a clean worktree
npm run test:run        # 649 passed (640 baseline + 9 new), 96 skipped
npm run quality         # clean (prettier + eslint --max-warnings 0 + tsc)
npm run build           # succeeds (~8s)
```

The 16 "Errors" reported by vitest are pre-existing MSW unhandled-rejection
noise from `SupplierConfigPage.test.tsx`; they predate this branch and are
swallowed by `dangerouslyIgnoreUnhandledErrors: true` in `vitest.config.ts`.

## Files touched

```
MakerMatrix/frontend/src/services/datasheet.service.ts                     (added)
MakerMatrix/frontend/src/services/__tests__/datasheet.service.test.ts      (added)
MakerMatrix/frontend/src/components/parts/PartPDFViewer.tsx                (modified)
MakerMatrix/frontend/src/components/parts/__tests__/PartPDFViewer.test.tsx (added)
MakerMatrix/frontend/src/pages/parts/PartDetailsPage.tsx                   (modified)
```
