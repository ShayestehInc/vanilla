# Stack profile: Flutter (mobile + desktop)

## Layout

| Thing             | Path                        |
| ----------------- | --------------------------- |
| App code          | `lib/`                      |
| Feature modules   | `lib/features/<feature>/`   |
| Unit/widget tests | `test/`                     |
| E2E tests         | `integration_test/`         |
| Generated code    | `*.g.dart`, `*.freezed.dart` (size-gate exempt) |

## Test commands

```bash
flutter analyze
flutter test
flutter test integration_test
dart format --set-exit-if-changed .
```

## Local certification block

```bash
run flutter analyze
run flutter test --reporter compact
# E2E only when the diff touches lib/ui or a navigation route:
# run flutter test integration_test
```

Set the gate roots so the known-failure scanner sees Dart:

```bash
KNOWN_FAIL_ROOTS="lib:.dart,test:.dart,integration_test:.dart" \
  python3 scripts/check_known_failures.py
```

## Platform

- Platform: mobile (+ desktop targets if enabled)
- Device matrix: small phone (e.g. iPhone SE), large phone (Pixel 8 Pro),
  tablet (iPad 11"). Test rotation and safe-area insets on each.
- Always exercised in the QA and Hacker stages:
  - **offline and flaky network** — the single biggest source of mobile-only bugs
  - **background / resume / cold start** with state restoration
  - **permissions** granted, denied, and denied-permanently
  - **OS back gesture** and deep links into a mid-stack route
  - **accessibility**: TalkBack/VoiceOver labels, dynamic text scale ≥ 200%

## UI

- State management: {{Riverpod / bloc / …}}
- Theming: a single `ThemeData` + token file; no hard-coded colours in widgets.
- Never hard-code sizes for a device; use `MediaQuery` / `LayoutBuilder`.

## Release surface

A shipped mobile build is a live API client that does not upgrade in lockstep
with the server. Treat any path/method/auth/payload/**enum value** change as
breaking, and say so explicitly in the PR. This is the `both`-platform contract
row in `CLAUDE.md`.

## Third-party providers

{{…}}
