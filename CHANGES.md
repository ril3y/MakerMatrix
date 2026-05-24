# Frontend quick-wins (uncommitted)

All eight items from the review are implemented. Run from `MakerMatrix/frontend/`.

## How to verify the whole batch

```bash
cd MakerMatrix/frontend
npm ci                                    # if you haven't installed yet
npm run quality                           # prettier + eslint (max-warnings 0) + tsc --noEmit
npm run test:run                          # vitest, all suites
rm -rf dist && npm run build              # production build
du -sh dist/assets                        # bundle size
```

## Bundle size (production build)

| | Before | After |
|---|---|---|
| Total `dist/assets/` | 2.8 MB | 3.0 MB |
| Initial entry chunk (`index-*.js`) | 2,821.51 kB | 165.64 kB |
| Initial entry gzip | 853.00 kB | 50.16 kB |

Per-route chunks are pulled in on navigation. Heavy vendor deps live in
their own chunks (`vendor-react`, `vendor-motion`, `vendor-charts`,
`vendor-syntax`) for long-lived browser caching. Total bytes went up
slightly because of chunk-boundary overhead, but the first paint payload
dropped ~94% which is the metric that matters for cold loads.

---

## 1. Route-level code splitting + vendor chunks

- `MakerMatrix/frontend/src/App.tsx` — every page route now uses
  `lazy(() => import(...))`. `Routes` wrapped in a `<Suspense>` boundary
  with the existing `LoadingScreen` as fallback.
- `MakerMatrix/frontend/vite.config.ts` — added
  `build.rollupOptions.output.manualChunks` for `react`/`react-dom`/
  `react-router-dom`, `framer-motion`, `react-syntax-highlighter`,
  `chart.js`/`react-chartjs-2`.

Test: `MakerMatrix/frontend/src/__tests__/App.lazy.test.tsx`
- 14 cases assert each lazy `import()` resolves to a renderable default
  export. If a page is moved/renamed, the matching case fails with the
  offending path. One additional case renders a lazy route inside
  `<MemoryRouter>` + `<Suspense>` to confirm Suspense integration works.

Reproduce:
```bash
npm run test:run -- src/__tests__/App.lazy.test.tsx
```

## 2. Modal a11y

- `MakerMatrix/frontend/src/components/ui/Modal.tsx`
  - Added `role="dialog"`, `aria-modal="true"`, `aria-labelledby` (auto-
    wires to a `useId`-generated id on the `<h2>` title), and optional
    `aria-describedby` via a new `describedById` prop.
  - When `showHeader={false}` the dialog falls back to `aria-label={title}`.
  - Close button has `aria-label="Close"` and `type="button"`.
  - Backdrop now has `role="presentation"` (Esc closes via the existing
    `useEscapeStack`, which is still in place).
  - Hand-rolled focus trap (no new dep — `react-focus-lock` was not
    already in `package.json`): on open, focus is moved to the first
    focusable inside the dialog (or the dialog itself if there are none);
    on close, focus is restored to whatever element opened the modal;
    Tab/Shift-Tab inside the dialog cycle within it.

Tests: `MakerMatrix/frontend/src/components/ui/__tests__/Modal.a11y.test.tsx` (7 cases)
- Role + `aria-modal` + `aria-labelledby` wiring.
- Close button has `aria-label="Close"`.
- `aria-label` fallback when `showHeader=false`.
- `aria-describedby` forwarding.
- Tab wraps focus back to the first focusable.
- Shift+Tab wraps focus to the last focusable.
- Focus restore after close.

The file ships a local `vi.mock('framer-motion', ...)` that wraps the
mocks in `forwardRef`, because the global `setup.ts` mock uses plain
function components and would swallow the ref the trap depends on.

Reproduce:
```bash
npm run test:run -- src/components/ui/__tests__/Modal.a11y.test.tsx
```

## 3. Strip `console.log` / `console.debug` + tighten lint

- Stripped 200+ `console.log`/`console.debug` call sites across 36 files
  in `MakerMatrix/frontend/src/` (kept `console.warn`/`console.error`/
  `console.info`). The worst offenders called out in the review are
  now silent:
  - `src/services/websocket.service.ts` — the line that printed the
    JWT in the WS URL is gone.
  - `src/pages/parts/PartsPage.tsx` — `handleSort` and `loadParts` debug
    logging is gone.
- `MakerMatrix/frontend/.eslintrc.json`
  - Tightened `no-console` to `["error", { "allow": ["warn", "error", "info"] }]`.
  - Added an `overrides` block so test files (`**/__tests__/**`,
    `*.test.*`, `*.spec.*`, `tests/**`) keep `no-console: off` — both
    vitest specs and Playwright helpers legitimately use `console.log`
    for output.
- Small cleanups left by the strip (empty `if/else` blocks, empty
  `useEffect` bodies, an `if (cond) {} else {...}` → `if (!cond) {...}`
  refactor in `AddPartModal.tsx`, etc.).
- One pre-existing test (`SettingsPage.appearance.test.tsx > logs when
  auto mode is selected`) was asserting that one of the stripped logs
  fired; rewritten to a "click doesn't throw" assertion since the log
  was the whole behavior under test.

Reproduce:
```bash
npm run lint                              # 0 errors, 0 warnings
```

## 4. Delete dead `.enhanced` services

Deleted:
- `MakerMatrix/frontend/src/services/categories.service.enhanced.ts`
- `MakerMatrix/frontend/src/services/locations.service.enhanced.ts`
- `MakerMatrix/frontend/src/services/__tests__/base-crud.test.ts`

Confirmed via grep first — the only references were the test importing
the two `.enhanced` services and the services importing each other's
base. The new `getErrorMessage` test (item 6) covers a more important
slice of the same module.

## 5. Remove `_priceTrends` zombie state

`MakerMatrix/frontend/src/pages/parts/PartDetailsPage.tsx`
- Removed the four underscore-prefixed `useState` declarations called
  out by the audit (`_priceTrends`, `_loadingPriceHistory`,
  `_availableSuppliers`, `_loadingAllocations`) plus their setters.
- Removed the 130-line "Order History & Price Trends" JSX block — it
  was guarded by `_priceTrends.length > 0`, which can never be true
  with the setter gone, so the chart was unreachable.
- Removed the now-unused `Line` import from `react-chartjs-2`.

## 6. Centralize axios error shape

- `MakerMatrix/frontend/src/services/api.ts`
  - Added `getErrorMessage(error: unknown, fallback?: string): string`
    that walks `response.data.detail` → `.message` → `.error` → `.message`
    and gracefully handles plain strings / non-error values.
  - Kept `handleApiError = getErrorMessage` as a backwards-compatible
    alias.
- Replaced every inline
  `as { response?: { data?: { detail?: string } } }` shape cast (8 sites
  across 6 files):
  - `src/store/authStore.ts` (3 sites in `login`, `guestLogin`,
    `updatePassword`)
  - `src/store/partsStore.ts` (3 sites in `loadParts`, `searchParts`,
    `loadPart`)
  - `src/components/users/EditUserModal.tsx` (2 sites — password change
    + role update)
  - `src/pages/suppliers/AddSupplierModal.tsx`
  - `src/pages/suppliers/AddSimpleSupplierModal.tsx`
  - `src/components/parts/AllocationsSummary.tsx`

Test: `MakerMatrix/frontend/src/services/__tests__/getErrorMessage.test.ts`
- 9 cases: prefers `detail` (FastAPI convention), falls back through
  `message` / `error`, falls back to the axios `.message`, returns the
  fallback for unknown shapes, handles plain strings, treats empty
  strings as missing, and the `handleApiError` alias.

Reproduce:
```bash
npm run test:run -- src/services/__tests__/getErrorMessage.test.ts
```

## 7. Hoist `MainLayout` nav items

`MakerMatrix/frontend/src/components/layouts/MainLayout.tsx`
- Moved `BASE_NAV_ITEMS` and `ADMIN_USERS_NAV_ITEM` to module scope so
  the JSX icon nodes are created once instead of on every render.
- The per-render combination now lives in a `useMemo` keyed on
  `isAdmin` + `hasPermission` identity.

## 8. Replace login full-reload — root cause fixed

**Diagnosis.** `generalWebSocket` and `taskWebSocket` are singletons that
were auto-connecting at module-load time
(`src/services/websocket.service.ts` lines 290-293,
`src/services/task-websocket.service.ts` lines 162-168). The connection
URL embeds the JWT (`?token=...`). At first page load the user is not
yet logged in, so the WS handshake either runs anonymously or with a
stale token from a previous session. After `login()` the new token is
written to `localStorage` by `authService.setAuthToken`, but the WS
connection has already been established — there was no listener to drop
the stale connection and reopen with the new token. The previous code
worked around this by full-reloading the page (`window.location.href =
...`) so the modules re-evaluated against the fresh token.

**Fix.**
- `src/services/websocket.service.ts` and
  `src/services/task-websocket.service.ts` — removed the module-load
  auto-connect blocks (replaced with a comment pointing at the new owner).
- `src/contexts/WebSocketContext.tsx` — now also imports
  `taskWebSocket`, subscribes to `useAuthStore`'s `user` + `isAuthenticated`
  via individual selectors, and runs an effect on auth-state change that
  disconnects both singletons and reconnects them. On logout it just
  disconnects. The effect's dep array includes `user?.id` so a re-login
  as a different user also re-handshakes.
- `src/pages/auth/LoginPage.tsx` — replaced
  `window.location.href = getPostLoginTarget()` with
  `navigate(getPostLoginTarget(), { replace: true })` for both
  `onSubmit` and `handleGuestLogin`. SPA navigation is now instant; the
  WS singletons reconnect with the right token in response to the
  auth-state flip.

## Files touched

```
MakerMatrix/frontend/.eslintrc.json                              (modified)
MakerMatrix/frontend/vite.config.ts                              (modified)
MakerMatrix/frontend/src/App.tsx                                 (modified)
MakerMatrix/frontend/src/components/layouts/MainLayout.tsx       (modified)
MakerMatrix/frontend/src/components/ui/Modal.tsx                 (modified)
MakerMatrix/frontend/src/contexts/WebSocketContext.tsx           (modified)
MakerMatrix/frontend/src/pages/auth/LoginPage.tsx                (modified)
MakerMatrix/frontend/src/pages/parts/PartDetailsPage.tsx         (modified)
MakerMatrix/frontend/src/services/api.ts                         (modified — getErrorMessage)
MakerMatrix/frontend/src/services/websocket.service.ts           (modified — removed auto-connect + logs)
MakerMatrix/frontend/src/services/task-websocket.service.ts      (modified — removed auto-connect + logs)
MakerMatrix/frontend/src/store/authStore.ts                      (modified)
MakerMatrix/frontend/src/store/partsStore.ts                     (modified)
MakerMatrix/frontend/src/components/users/EditUserModal.tsx      (modified)
MakerMatrix/frontend/src/components/parts/AllocationsSummary.tsx (modified)
MakerMatrix/frontend/src/pages/suppliers/AddSupplierModal.tsx    (modified)
MakerMatrix/frontend/src/pages/suppliers/AddSimpleSupplierModal.tsx (modified)
~30 other files with stripped console.log/debug calls            (modified)

MakerMatrix/frontend/src/services/categories.service.enhanced.ts (deleted)
MakerMatrix/frontend/src/services/locations.service.enhanced.ts  (deleted)
MakerMatrix/frontend/src/services/__tests__/base-crud.test.ts    (deleted)

MakerMatrix/frontend/src/__tests__/App.lazy.test.tsx                       (added)
MakerMatrix/frontend/src/components/ui/__tests__/Modal.a11y.test.tsx       (added)
MakerMatrix/frontend/src/services/__tests__/getErrorMessage.test.ts        (added)
```

## Test results

- `npm run quality` — passes (format + lint 0 warnings + tsc).
- `npm run test:run` — 640 passed, 96 skipped, 0 failed.
  - The 16 reported "Errors" are pre-existing MSW unhandled-rejection
    noise from `SupplierConfigPage.test.tsx` and are already swallowed
    by `dangerouslyIgnoreUnhandledErrors: true` in `vitest.config.ts`.
- `npm run build` — succeeds.
