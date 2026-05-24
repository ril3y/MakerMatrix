# `fix/ts-strict-clear` — clear all `@ts-nocheck` deferrals

## Summary

- **29 files cleared** (every file listed in `TS_STRICT_DEFERRED.md`).
- **91 → 0 strict-mode type errors.** `npm run type-check` exits 0 with no
  escape hatches (`@ts-nocheck`, `@ts-ignore`, `@ts-expect-error`, or new
  `any`).
- **0 deferrals remain.** `TS_STRICT_DEFERRED.md` is now a stub describing
  the policy going forward.
- Tests: 631 passed / 96 skipped (matches baseline). 16 unhandled rejections
  are the same MSW warnings present on `cleanup/ci-infra-hygiene`.
- Build: `npm run build` succeeds. Bundle: `index-*.js` 2.82 MB (853 KB gzip).
- Lint: `npm run lint` clean (0 errors, 0 warnings — `quality:fix` normalized
  CRLF endings on touched files).

## Files touched

Frontend sources where `@ts-nocheck` was removed and types fixed (29):

```
src/__tests__/mocks/handlers.ts
src/components/categories/EditCategoryModal.tsx
src/components/import/ImportSelector.tsx
src/components/import/hooks/useOrderImport.ts
src/components/locations/AddLocationModal.tsx
src/components/locations/EditLocationModal.tsx
src/components/locations/LocationDetailsModal.tsx
src/components/parts/AddPartModal.tsx
src/components/parts/PartEnrichmentModal.tsx
src/components/parts/__tests__/AddPartModal.test.tsx
src/components/printer/DynamicPrinterModal.tsx
src/components/printer/PrinterModal.tsx
src/components/ui/EmojiPicker.tsx
src/components/ui/__tests__/ThemeSelector.test.tsx
src/hooks/useFormWithValidation.ts
src/pages/parts/EditPartPage.tsx
src/pages/parts/PartDetailsPage.tsx
src/pages/parts/PartsPage.tsx
src/pages/settings/SettingsPage.tsx
src/pages/suppliers/DynamicAddSupplierModal.tsx
src/pages/suppliers/EditSupplierModal.tsx
src/pages/suppliers/SupplierConfigPage.tsx
src/pages/suppliers/SupplierConfigPage.test.tsx
src/pages/tools/ToolsPage.tsx
src/services/parts.service.ts
src/services/task-websocket.service.ts
src/services/__tests__/base-crud.test.ts
src/services/__tests__/pdf-proxy.test.ts
src/store/__tests__/stores-refactoring.test.ts
```

Collateral edits required to make strict mode honest (4):

```
src/components/suppliers/CredentialEditor.tsx   # form.watch returns
                                                # PathValue, not always
                                                # string — coerce before
                                                # .length.
src/contexts/ThemeContext.tsx                   # export ThemeContextType
                                                # so a test can assert null
                                                # behavior with a proper
                                                # type cast.
src/store/locationsStore.ts                     # getLocationsByParent now
                                                # normalizes null/undefined
                                                # parent_id (real bug
                                                # surfaced by typing).
MakerMatrix/frontend/TS_STRICT_DEFERRED.md      # collapsed to a policy
                                                # stub now that the table
                                                # is empty.
```

## Real bugs found

1. **`pages/parts/EditPartPage.tsx:258`** — `{ name, quantity, ...data }`
   with `...data` *after* the named keys made TS2783 fire. The object spread
   silently overwrote the explicit values, clearly not intended. Reordered
   so the explicit keys win.
2. **`pages/parts/PartDetailsPage.tsx:947, 1578, 1626`** — `canUpdate` from
   `usePermissions()` is a *function*, but three sites were treating it as a
   boolean (`if (!canUpdate)` / `${canUpdate && ...}`). The conditions were
   always truthy, so permission gating was a no-op at those sites. Now
   invoked as `canUpdate('parts')`.
3. **`services/parts.service.ts`** — `delete backendData.name` and
   `... = null` on required string fields were the obvious anti-pattern
   strict mode flagged. Switched to destructuring and used `undefined` to
   omit foreign-key fields, matching the request DTO.
4. **`store/locationsStore.ts:getLocationsByParent`** — signature accepts
   `string | null`, but `Location.parent_id` is `string | undefined`. Strict
   equality meant `getLocationsByParent(null)` never matched a root location
   stored without an explicit `parent_id`. Now normalizes both sides to
   `undefined`.

## Patterns used

- **`null` → `undefined` on persistence DTOs.** `Location`,
  `CreateLocationRequest`, `Part` all declare `parent_id`/`image_url` etc.
  as `string | undefined`. Tests and call sites that were passing `null`
  for "root / cleared" now pass `undefined` or omit the field. The DB
  layer treats both as "no value", so behavior is preserved.
- **`Boolean(x) && <JSX/>` for `unknown`-typed conditionals.**
  `additional_properties` is `Record<string, unknown>`; bare `&&` would
  return the unknown value if truthy, which is not a valid `ReactNode`.
  Wrapping the test in `Boolean(...)` converts the type to `boolean`
  without changing behavior.
- **`?? undefined` to widen `null` to `undefined`** at component prop
  boundaries (e.g. `error={nameError ?? undefined}`,
  `selectedPrinterForEdit ?? undefined`).
- **`Record<string, ...>` casts on hand-rolled literal lookup tables**
  (`EMOJI_KEYWORDS`, `_getIconForProperty`) so a `string` index is allowed.
- **Zod schemas with `.default()`** make the inferred input type allow
  `undefined` while the output is required — incompatible with
  `z.ZodSchema<T>` invariance. `AddLocationModal` uses a one-line cast
  `as unknown as z.ZodType<LocationFormData>` to bridge this.
- **`react-hook-form`'s `watch()` overloads** disagreed on `watch(undefined)`
  vs `watch(name)`. Split the no-arg case explicitly in
  `useFormWithValidation`.
- **WebSocket handler variance:** `TaskWebSocketMessage` is narrower than
  `WebSocketMessage`, so a handler typed on the narrow shape is not
  assignable to the wider event registry. Switched the `wrapped` callbacks
  to take `WebSocketMessage` and cast inside.

## Verification

```
cd MakerMatrix/frontend
npm run type-check   # exit 0, zero strict-mode errors
npm run lint         # exit 0, zero warnings
npm run build        # exit 0, ~2.82 MB / 853 KB gzip
npm run test:run     # 631 passed, 96 skipped, 0 new failures vs. baseline

# Verify no remaining @ts-nocheck escape hatches:
grep -rln "@ts-nocheck" MakerMatrix/frontend/src   # no matches
```
