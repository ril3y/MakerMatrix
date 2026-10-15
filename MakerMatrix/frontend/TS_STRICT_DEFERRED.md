# TypeScript strict-mode deferred files

`tsconfig.json` is set to `"strict": true`. As of branch `fix/ts-strict-clear`,
**all previously deferred `@ts-nocheck` directives have been removed** and the
underlying type errors fixed. `npm run type-check` exits 0 with no escape
hatches.

If you re-introduce strict-mode failures, fix them at the call site rather than
adding `@ts-nocheck`. See `CHANGES.md` for the patterns used during the
cleanup sweep.
