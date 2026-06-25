# Shatranj Source Layout

This is the canonical source map. Keep new files inside the matching domain;
do not place loose `.c`, `.h`, or `.asm` files at the old root paths.

## Common Code

- `src/common/chess/`: host-side chess position, FEN, and legal-move wrapper
  code used by tests and the PC client.
- `src/common/mqtt/`: MQTT packet encoder/parser used by host tests and PC
  code. Spectrum has its own size-constrained MQTT path.
- `src/common/protocol/`: Shatranj game/session message grammar parse/build
  helpers shared by clients where practical and kept host-testable.

## Spectrum Code

- `src/spectrum/app/`: top-level Spectrum state machine, input flow, turn
  control, and application orchestration.
- `src/spectrum/config/`: Spectrum session/options configuration shared by
  app, transport, UI overlays, and tests without depending on `app/`.
- `src/spectrum/session/`: connection/session state helpers such as ping/loss
  policy and cooperative link polling, kept free of UI, board, app, and overlay
  dependencies.
- `src/spectrum/board/`: Spectrum board state, parsed move application, and
  compact rules reference code. It may dispatch cold board/rules overlays only
  through `spectrum/overlay/overlay.h`; overlay internals stay private.
- `src/spectrum/ui/`: GUI state, status bar, timers, chat/move rendering, and
  input rendering. UI owns a copied board snapshot pushed by `app`; it must not
  include board internals or cache board-owned pointers.
- `src/spectrum/transport/`: app-facing link facade, ESP AT networking, raw TCP
  bridge mode, MQTT packet transport, direct keepalive grammar, and link-level
  buffers. Text protocol parse/build belongs in `src/common/protocol/`. It may
  dispatch cold network overlays only through `spectrum/overlay/overlay.h`;
  overlay internals stay private.
- `src/spectrum/platform/`: Spectrum platform wrappers for frame wait, UART,
  text append helpers, and cold-path runtime hooks used by networking.
- `src/spectrum/overlay/`: C bridge for cold overlays. UI includes are
  allowlisted: cold overlays may use `ui/layout.h` for coordinates,
  `overlay_api.h` may expose the minimal info-panel ABI, and `overlay.c` may use
  `ui/gui.h` as resident dispatch glue.

## PC Code

- `src/pc/client/`: Qt PC client source.
- `client/`: PC client build wrappers and project files only.

## Assembly

- `asm/spectrum/`: direct ZX screen and text rendering.
- `asm/uart/`: DIVMMC/divTIESUS UART backend.
- `asm/esxdos/`: esxDOS file/overlay loader code.
- `asm/platform/`: small platform primitives such as HALT.
- `asm/overlay/rules/`: cold rules overlay entry and implementation.

ChessZX is a visual/architectural reference for board/UI flow and piece asset
organization; do not vendor its source without a clear license.

## Assets

- `assets/spectrum/`: Spectrum-specific binary and ASM assets.

## Tests

- `tests/rules/`: chess wrapper tests.
- `tests/net/`: MQTT, game-protocol, MQTT-session, and keepalive grammar host
  tests.
- `tests/spectrum/`: Spectrum board/rules, config, and session host checks.

## Boundaries

- Transport decides how bytes move, not whether a chess move is legal.
- Protocol defines payload grammar, not UI state.
- UI renders state and input feedback, not session negotiation rules.
- Overlays hold cold Spectrum logic that should not inflate resident 48K code.
