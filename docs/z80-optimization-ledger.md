# Z80 Optimization and Evidence Ledger

Status: completed software and physical-evidence ledger, 2026-08-17.
Measurements come from linked Classic/Next artifacts and the recorded physical
results; estimates are never added together. H1 and H3 passed on hardware.
H2 was physically characterised and closed as unsupported pre-session traffic,
not left pending.

## Preserved behaviour and hard limits

- Preserve protocol, wire/save formats, overlay ABI, AT command ordering,
  visible strings, chess legality, and interrupt/MMU ownership.
- The FILEUI S4 experiment may intentionally switch the displayed timestamp
  to the FAT timestamp supplied by the directory entry.
- Every overlay must remain at or below 2048 bytes.
- The linked SP gap must remain at least 512 bytes; 768 bytes is the warning
  threshold.
- Do not move overlay-only code resident and do not update baselines merely to
  accept growth.

## Measured result

| Target | Fresh audit resident | Final resident | Net | Final SP gap | Tightest final overlay |
| --- | ---: | ---: | ---: | ---: | --- |
| Classic | 34858 | 34739 | -119 | 1547 | RESTORE 1926/2048 |
| Next | 35596 | 35479 | -117 | 707 | MQTT_CONNECT 1997/2048 |

S6/S8/S9/S10 save 122 resident bytes on both targets. The retained IM1
hardening costs two bytes on Next, hence the optimization block's net -120.
The integrated main includes three additional resident bytes from intervening
protocol commits, producing the table totals above. S4 and S5 additionally
save 315 and 107 bytes in their overlays on both targets. The RTC year predicate
is unchanged and now has explicit tests for 2024, 2035, and 2036.

## Option ledger

| ID | Candidate | Acceptance | Status / measured result |
| --- | --- | --- | --- |
| S1 | Compact Next MQTT_CONNECT | Preserve AT behaviour; save at least 50 overlay bytes; zero resident cost | Rejected and reverted after two measured designs. Fixed table/probe saved 7 then 17 bytes total. A distinct `at_cmd_med` helper passed focused tests but saved only 13 bytes Classic and 18 bytes Next (1997 -> 1979), below the 50-byte rule. |
| S2 | Pack `gui_msg_blob` | Preserve all text; save overlay bytes; scratch <=26 bytes | Rejected and reverted. Six-token expander passed text tests but grew GUI_LOG 1889 -> 1953 (+64 bytes). Decoder cost exceeded blob saving. |
| S3 | Arithmetic RESTORE base64 | Preserve NCZS wire/CRC; save overlay bytes | Rejected and reverted. Arithmetic URL-safe mapper passed wire/invalid-boundary tests but grew RESTORE 1926 -> 1996 (+70 bytes). SDCC branch cost exceeded the 65-byte table. |
| S4 | Use FILEUI dirent FAT stamp | Preserve list/save/load; save overlay bytes; record visible timestamp change | Accepted: FILEUI 1913 -> 1598 (-315 bytes) on Classic and Next. Filename timestamp decoder/state removed; rows now use the esxDOS dirent FAT stamp promised by the file contract. Classic emulator saved `GAME1`, listed `17-08-26 02:51`, completed RQ/RY + RS00/RS01 + RA, and returned to the board with `RESTORED`. |
| S5 | Merge white/black RULES twins | Perft, castling, EP, hints green; save overlay bytes | Accepted: shared parameterized pawn/castling paths reduce RULES 1903 -> 1796 (-107 bytes). Board tests, compact perft, and Python oracle (205 move sets, 416 perft checks) pass. |
| S6 | Pool three duplicated resident strings | One linked copy each; 50 bytes | Accepted: 50 bytes on Classic and Next |
| S7 | Replace `strcmp` library pull | Preserve five comparisons; remove `asm_strcmp`; save resident bytes | Rejected and reverted. Portable+ASM equality helper passed protocol tests but its body was about 36 bytes versus the existing 23-byte `strcmp` pull, before call-site effects. |
| S8 | Factor moves/chat list/address ASM | Preserve rendering; save resident bytes | Accepted on narrower second design: shared move/chat single-row address/Y setup saves 28 linked resident bytes after subtracting the exact S9/S10 spans. Classic emulator rendered a local move/ACK and remote `CHAT hello` through the shared paths. |
| S9 | Share `net_copy`/`net_move` load | Preserve transport copies; save resident bytes | Accepted: `net_copy` tail-jumps to the overlap-safe `net_move`; both public symbols remain. Exact linked span 25 -> 2 (-23 bytes); ASM vectors and network/session tests pass. |
| S10 | Share token/digit load | Preserve parsers; save resident bytes | Accepted: carry selects token/digit after one shared packed-argument prologue. Exact linked token-to-copy-rest span 112 -> 91 (-21 bytes); updated mutation vector and protocol tests pass. |
| S11 | Establish IM1 in Next hard reset | Remove the CRT/NEX-loader IM-mode assumption before `EI; HALT`; preserve reset timing | Accepted: exact CRT disassembly showed IM1 only on the CRT exit path, so `_net_uart_hard_reset` now executes `IM 1` while DI before its first EI. Cost: +2 Next resident bytes; no Classic cost. Boot expansion was traced restoring MMU0/MMU1/MMU2 before EI. |

## Evidence backlog

| ID | Evidence task | Completion rule | Status |
| --- | --- | --- | --- |
| E1 | Reliable `.c.asm`/`.lst` output | Inspect exact generated code for the questioned inline ASM | Accepted during the audit: exact z88dk 2.4 generated CONNECT and TX listings; TX proved BC/DE are reloaded after RTC inline ASM and no compiler temporary is live across the block. The disposable listing generator and artifacts were removed after the audit at the user's request. |
| E2 | Exact CI toolchain | `make full-check` with `z88dk/z88dk:2.4` | Accepted: exact z88dk 2.4 full gate passes; final linked sizes are recorded above. |
| E3 | Emulator acceptance | Classic/Next boot plus affected DIRECT/UI/load paths | Accepted for emulator scope: current staged TAP and NEX boot. Classic DIRECT completed handshake/start, `MOVE 1 e2e4`/`ACK 1 e4`, CHAT rendering, and FILE list/save/load. The virtual modem suite passes 9/9. Physical H1/H3 passed and H2 was characterised and closed. |
| H1 | NextZXOS `$5B00` RTC clobber probe | Real Next UART ring remains coherent across RST 8 `0x92`/`0x8E` | **Physical PASS, 2026-08-17:** key 1 reported `H1 RTC/RING PASS`, `CHANGED 0000`, FAT date `$5C11`, time `$4EA0`, service 1 (`0x92`). The exact `$5B00..$5BFF` canary remained intact. |
| H2 | RX during long DI | Characterise cold-load RX and decide whether preservation is a product requirement | **Closed as an architectural boot behaviour, 2026-08-17.** A physical 800-fps run received `$09A3` frames and reported 2 breaks/3 malformed frames across the exact expansion; another 800-fps run could not establish a clean pre-expansion baseline. Byte preservation is therefore not guaranteed under a synthetic cold-load flood. This is not a reachable session failure: expansion runs only before connection setup, after which production calls `spectrum_net_start_uart`, discards pending RX for 25 frames, and runs Next-specific command/baud recovery before creating a session. BridgeZX + RESET recovered without a power cycle. Adding a resident ring/pump would spend scarce Next memory for an unsupported pre-session stream, so it is rejected. Diagnostic logs and fixtures were removed after recording this result. |
| H3 | Hard-reset/dirty-link recovery | Physical ESP reset, transparent recovery, and reconnect succeed | **Physical PASS, 2026-08-17:** ESP/local UART recovered from 230400 to 115200; transparent recovery succeeded and the Mac received the test payload from the real Next; physical reset reported `PASS` and `AT VERIFIED` on all 3/3 repetitions. Diagnostic logs and fixtures were removed after recording the result. The IM1 prerequisite is S11. |

## Retained constraints and tradeoffs

- Next remains tight: SP gap is 707 bytes (hard floor 512, warning below 768)
  and MQTT_CONNECT is 1997/2048. This is not discarded; it is the reason every
  future resident or CONNECT change still needs exact multi-target sizing.
- Classic keeps the overlay slot at `$6800` and ZX data origin at `$7000` in
  contended RAM. The resident UART read path is above `$8000`; overlay polling
  and RST 8 do not introduce `EI; HALT`. Moving this architecture would cost
  more memory and is not justified by a reproduced failure.
- RTC dates 2024..2035 use the Next RTC path. From 2036 the existing predicate
  deliberately rejects the FAT date and falls back to SNTP; the misleading
  comment was fixed, but the behavior and wire format were preserved.
- No committed size/ABI baseline was loosened. Generated maps, listings, TAP,
  OVL, DAT, and NEX remain build artifacts rather than edited source.

## Closed audit leads

The stack/carry/callee-pop/IY/UART-NUL/MMU/pump/render/FRAMES candidates and
the RTC/About/FILEUI-slot/SEND-OK/buffer/NACK+SYNC/flip-hints second-pass leads
were traced and rejected as defects. They require no production change unless
new runtime evidence contradicts the audit.

## SAN ASM / streq experiment (2026-08-21)

Disposable worktree only (`Temp/shrink-ncx/wt-2b3e6c4a`), detached `1189095`
plus the uncommitted IY wraps. Not on `main`. `docs/size_report.baseline.json`
is stale versus HEAD+IY; A/B used a same-rev IY-only build.

| Target | IY-only CODE_FULL | After SAN+streq | Δ | SP_GAP Δ | OVL |
| --- | ---: | ---: | ---: | ---: | ---: |
| Classic | 35357 | 35057 | -300 | +300 | 0 |
| Next | (same SAN object) | resident 35329 | -303 vs IY 35632 | +300 | 0 |

SAN overlay-move (old S1) rejected: `is_legal_move_coords` loads RULES.

P0: `pop hl` after `_spectrum_board_is_legal_move_coords` clobbered L. Fixed
by saving L before the pops. Locked by `tests/spectrum/san_vector.asm` (g1f3,
four rook forms, suffix, fail NUL) plus a mutant that restores the clobber.

| ID | Item | Decision |
| --- | --- | --- |
| SAN-IX | Dead `push ix`/`pop ix` | Done. Function never uses IX; 6 code bytes. |
| SAN-CELLS0 | Discarded first `board_cells` in disambig | Done. 5 code bytes. 64× loop call left (speed, ~0 size). |
| SAN-LEN | ASM returns 1, C returns `san_len` | Documented in `san.h`. Callers only test `!= 0`. |
| SAN-NUL | No `out[0]='\\0'` before parse | Done. 2 code bytes; fail path now matches C. |
| SAN-ADD | `san.asm` untracked | Deferred until an explicit land-on-branch request. |
