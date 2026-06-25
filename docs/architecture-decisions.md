# Shatranj Architecture Decisions

## 0001 - Project Name

Decision: visible product name is Shatranj.

Reason: Shatranj is the visible product name; protocol/internal prefixes stay
stable for compatibility.

Current generated names:

- Spectrum TAP: `SHATRANJ.tap`
- PC client: `shatranj-client.exe`
- Protocol prefix: `netchesszx/v1`

## 0002 - Chess Core Layout

Decision: do not restructure the repository around `mcu-max`.

Use this layout instead:

```text
src/
  common/
    chess/
    mqtt/
    protocol/
  pc/
    client/
  spectrum/
    app/
    board/
    overlay/
    platform/
    transport/
    ui/
asm/
  spectrum/
  uart/
  esxdos/
  platform/
  overlay/rules/
third_party/
  mcu-max/
client/
tests/
```

Reason: `mcu-max` is engine logic, not application architecture. Shatranj has
separate responsibilities: Spectrum transport, PC GUI, protocol, build outputs,
and later MQTT. Keeping `mcu-max` in `third_party` makes updates/replacement
possible without coupling the whole project to upstream layout.

Integration contract:

- `third_party/mcu-max`: imported upstream source, kept unmodified.
- `src/common/chess`: Shatranj-owned wrapper and board/FEN API.
- `tests/rules`: perft and special-rule tests against the wrapper.
- `src/pc/client`: consumes wrapper behavior first on PC.
- Spectrum build: includes only the wrapper subset proven to fit memory.
- `docs/source-layout.md`: canonical source map for current paths.

Current caveat: `mcu-max` does not support underpromotion. Shatranj v0 accepts
queen promotion and rejects rook/bishop/knight promotion until we add or replace
that part.

## 0003 - Spectrum Renderer

Decision: Spectrum screen rendering starts in ASM.

Reason: the C `printf` board was useful for transport proof but too slow and too
large. Screen clear, board drawing, cursor, attributes, and later piece blits
need direct VRAM writes from the beginning.

Boundary:

- C keeps protocol/network orchestration while it remains cheap enough.
- ASM owns rendering hot paths.
- ChessZX is a reference for UI/piece organization, not vendored code.

## 0004 - Spectrum Cold Overlays

Decision: keep the Spectrum resident core 48K-first and add a Spectalk-style
cold overlay file, `SHATRANJ.OVL`.

Reason: legal move validation, storage, options, and reconnect/resume logic are
cold paths. Keeping them resident would force a premature 128K-only boundary and
make later memory recovery harder.

Current contract:

- Resident owns UI, board drawing, network/protocol, timers, and turn state.
- `asm/esxdos/overlay_loader.asm` loads fixed 2048-byte blocks from `SHATRANJ.OVL`
  into `_overlay_code_slot`.
- Overlay 0 is reserved for chess rules.
- Local Spectrum moves are not applied locally until the PC returns `ACK <ply>`.
  If the PC rejects a move, it sends `NACK <ply> ...`; the Spectrum keeps the
  turn and board state.

This gives a safe protocol guard immediately while the full rules overlay is
filled in.
