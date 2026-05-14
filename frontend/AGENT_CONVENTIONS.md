# Frontend Agent Conventions

## Read Order

When working on frontend tasks, always read this file before implementation and use it together with `AGENTS.md` and `CLAUDE.md`.

## Architecture Constraints

- Follow App Router boundaries in `src/app/`, keep business logic in `src/core/`.
- Prefer existing thread hooks and existing stores before creating new state systems.
- Reuse components in `src/components/ui/` and `src/components/workspace/` before adding new primitives.
- Keep API communication in `src/core/api/` or feature-specific core modules.

## Coding Style

- TypeScript first: explicit types for public APIs, hook return values, and data contracts.
- Keep components focused; extract utilities for reusable logic.
- Prefer immutable updates and deterministic merge logic.
- Reuse i18n keys in `src/core/i18n/locales/` instead of inline user-facing strings.

## State Management Constraints

- Persist browser-side preferences via `src/core/settings/`.
- Use `useSyncExternalStore` for shared localStorage-backed state that needs reactive updates.
- Add stable storage keys with `deerflow.` prefix.
- Keep conflict-resolution behavior explicit and testable.

## Validation & Testing

- For setting or memory related behavior, add unit tests under `tests/unit/core/`.
- Run `pnpm check` after substantial changes.
- Ensure import/export flows validate payload shape and handle malformed JSON safely.

## Do Not Modify

- Do not manually edit generated UI primitives in `src/components/ui/` and `src/components/ai-elements/`.
- Do not move thread ownership boundaries defined in `AGENTS.md` unless explicitly requested.
