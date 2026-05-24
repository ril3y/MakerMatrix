# TypeScript strict-mode deferred files

`tsconfig.json` was switched from `"strict": false` to `"strict": true`. The
files below already failed under strict mode at the time of the switch and
carry a `// @ts-nocheck` directive at the top so that `npm run type-check` and
`npm run build` stay green for the rest of the codebase.

Each entry lists the file, the number of errors observed at activation, and
the dominant error class. Removing the `// @ts-nocheck` line should be the
first step when picking one of these up.

## Source files (build-blocking when un-deferred)

| File                                                | Errors | Notes                                                                                                         |
| --------------------------------------------------- | ------ | ------------------------------------------------------------------------------------------------------------- |
| `src/pages/parts/PartDetailsPage.tsx`               | 14     | Mixed: implicit any indexing, null/undefined ReactNode coercion, optional chains. Largest by far.             |
| `src/services/task-websocket.service.ts`            | 10     | `TaskWebSocketMessage` vs `WebSocketEventHandler` variance — registry callback typing needs a narrow generic. |
| `src/services/parts.service.ts`                     | 5      | `null` vs `string \| undefined` mismatch on serialization; `delete` on required field.                        |
| `src/components/locations/EditLocationModal.tsx`    | 5      | Same null/undefined mismatch around `image_url`/`parent_id`.                                                  |
| `src/pages/parts/PartsPage.tsx`                     | 3      | `Object is possibly undefined` on array access, `unknown` ReactNode.                                          |
| `src/components/parts/AddPartModal.tsx`             | 3      | `string \| null` → `string \| undefined` for form defaults.                                                   |
| `src/components/import/ImportSelector.tsx`          | 3      | `never[]` inferred for supplier list — needs explicit type.                                                   |
| `src/pages/tools/ToolsPage.tsx`                     | 2      | `boolean \| ""` from short-circuit; tag mapping type.                                                         |
| `src/pages/suppliers/EditSupplierModal.tsx`         | 2      | Supplier field schema does not match shared type.                                                             |
| `src/pages/suppliers/DynamicAddSupplierModal.tsx`   | 2      | `Record<string, string \| number \| boolean>` vs `CredentialValue`.                                           |
| `src/pages/parts/EditPartPage.tsx`                  | 2      | Duplicate keys in object spread (TS2783) — likely a real bug.                                                 |
| `src/hooks/useFormWithValidation.ts`                | 2      | `err.response.data` narrowing; overload mismatch.                                                             |
| `src/components/printer/DynamicPrinterModal.tsx`    | 2      | Optional `recommendations`; `delete` on required field.                                                       |
| `src/components/locations/LocationDetailsModal.tsx` | 2      | `string \| undefined` → `string`.                                                                             |
| `src/components/import/hooks/useOrderImport.ts`     | 2      | `failed_count`/`skipped_count` optional.                                                                      |
| `src/components/categories/EditCategoryModal.tsx`   | 2      | `data.name` optional handling.                                                                                |
| `src/pages/suppliers/SupplierConfigPage.tsx`        | 1      | `err is unknown` — needs an `instanceof Error` narrow.                                                        |
| `src/pages/settings/SettingsPage.tsx`               | 1      | Printer object literal mismatch with `Printer` type.                                                          |
| `src/components/ui/EmojiPicker.tsx`                 | 1      | Implicit any on indexed-object lookup.                                                                        |
| `src/components/printer/PrinterModal.tsx`           | 1      | `boolean \| ""` from short-circuit.                                                                           |
| `src/components/parts/PartEnrichmentModal.tsx`      | 1      | `unknown` ReactNode.                                                                                          |
| `src/components/locations/AddLocationModal.tsx`     | 1      | Zod schema variance — likely fixed with `as ZodType<...>`.                                                    |

## Test files (do not block production build but block `npm run type-check`)

| File                                                   | Errors |
| ------------------------------------------------------ | ------ |
| `src/store/__tests__/stores-refactoring.test.ts`       | 7      |
| `src/services/__tests__/base-crud.test.ts`             | 6      |
| `src/__tests__/mocks/handlers.ts`                      | 5      |
| `src/services/__tests__/pdf-proxy.test.ts`             | 3      |
| `src/pages/suppliers/SupplierConfigPage.test.tsx`      | 1      |
| `src/components/ui/__tests__/ThemeSelector.test.tsx`   | 1      |
| `src/components/parts/__tests__/AddPartModal.test.tsx` | 1      |

## Recommended cleanup order

1. The five-error files (`parts.service.ts`, `EditLocationModal.tsx`) share the
   same `null` vs `undefined` mismatch on persistence DTOs. Fix the shared
   schema and several of these will fall together.
2. `task-websocket.service.ts` — type the registry with `<T extends WebSocketMessage>`.
3. Test fixtures (`stores-refactoring.test.ts`, `base-crud.test.ts`,
   `mocks/handlers.ts`) — should be a quick batch once the DTO `null`/`undefined`
   story is unified.
4. `PartDetailsPage.tsx` — biggest file; budget for its own session.
