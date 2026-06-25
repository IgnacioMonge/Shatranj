# Shrink notes

## Accepted changes

- `src/spectrum/board/board.c`: `spectrum_board_parse_move_coords()` now derives
  file/rank indexes first and validates the four `uint8_t` values with `>= 8u`.
  This keeps invalid ASCII coordinates rejected while avoiding duplicated range
  checks. Trimmed CODE dropped from 33248 to 33174 bytes. Accepted: -74 bytes.
- `src/spectrum/board/board.c`: `rules_piece_from_char()` now uses compact
  piece/value lookup tables instead of a 12-case switch. Trimmed CODE dropped
  from 33174 to 33150 bytes. Accepted: -24 bytes.
- `src/spectrum/ui/gui.c`: merged identical `display_row()` and `display_col()`
  helpers into one `display_coord()` helper. Trimmed CODE dropped from 33150 to
  33115 bytes. Accepted: -35 bytes.

## Resolved experiments

- Direct transport now always uses the DIRECT overlay path. The old
  `NETCHESSZX_USE_DIRECT_OVERLAY` build switch and resident Direct fork are
  removed to avoid divergent fixes and accidental non-overlay builds.
- ASM-port audit resolved: no candidate from the old C-to-Z80 list justified an
  immediate ASM rewrite. `spectrum_gui_animate_board_pieces` is frame-gated and
  already uses ASM for VRAM work; `spectrum_mqtt_parse_publish` already uses a
  bounded two-byte VLI path; UART overrun needs measurement before any ring
  buffer rewrite; `menu_logic_visible_has_row` belongs as a C simplification if
  needed; `board_flip_square_unchanged` and GUI log copy work are marginal.

## Rejected experiments

- `src/spectrum/transport/net.c`: replacing the single `strcat(direct_tx_payload, "\n")`
  path with manual bounded copy removed the `strcat` map symbol, but z88dk output grew
  from 33248 to 33270 trimmed CODE bytes. Rejected: +22 bytes.
- `src/spectrum/transport/net.c`: replacing `strcmp(last_ip, "0.0.0.0")`
  with fixed character comparisons grew trimmed CODE from 33248 to 33302 bytes.
  Rejected: +54 bytes.
- `src/spectrum/transport/mqtt_min.c`: replacing `put_bytes()` `memcpy` with a
  local byte-copy loop grew trimmed CODE from 33248 to 33260 bytes. Rejected:
  +12 bytes.
- `src/spectrum/app/app.c`: replacing three `"Select options"` literals with a
  shared `static const char[]` produced no size change. Rejected as noise.
- `src/spectrum/board/board.c`: replacing the compact `rules_piece_from_char()`
  lookup table with uppercase normalization plus a 6-case switch grew trimmed
  CODE from 33150 to 33254 bytes. Rejected: +104 bytes.
- `src/spectrum/board/board.c`: deriving `rules_piece_from_char()` return values
  from the lookup index instead of a `values[]` table grew trimmed CODE from
  33150 to 33169 bytes. Rejected: +19 bytes.
- `src/spectrum/board/board.c`: replacing `piece_side()` range checks with the
  lowercase bit produced no trimmed CODE change. Rejected as extra precondition
  without size benefit.
- `src/spectrum/ui/gui.c`: replacing five `strncpy()` + explicit terminator
  copies with a local bounded-copy helper grew trimmed CODE from 33150 to 33210
  bytes. Rejected: +60 bytes.
- `src/spectrum/ui/gui.c`: replacing fixed-string `memcpy()` calls for timer and
  clock labels with direct character assignments grew trimmed CODE from 33150 to
  33232 bytes. Rejected: +82 bytes.
- `src/spectrum/ui/gui.c`: factoring the three `spectrum_gui_notify*()` setup
  paths into a parameterized helper grew trimmed CODE from 33115 to 33119 bytes.
  Rejected: +4 bytes.
- `src/spectrum/app/app.c`: replacing `mqtt_payload_origin()` library string
  checks with fixed byte comparisons grew trimmed CODE from 33115 to 33372
  bytes. Rejected: +257 bytes.
