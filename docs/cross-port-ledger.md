# Cross-Port Ledger (MirrorShift)

MirrorShift (`C:/dev/MirrorShift`, remote `mirrorshift`) is a separate product
built from a copy of this tree. The two repositories share no Git history, so
there is no upstream/downstream relationship: improvements travel in both
directions and each one is a deliberate decision, not an automatic merge.

This file records what has crossed, what was rejected, and why. Update it in
the same change that ports something.

## Sync Mechanism

`git cherry-pick` works across unrelated histories: it three-way merges by path,
and every shared file keeps the same path in both trees.

```
git fetch mirrorshift
git log mirrorshift/main --oneline                  # what is new there
git diff mirrorshift/main -- src/common/session/    # divergence in one area
git cherry-pick -x <sha>                            # apply
```

`-x` records the source SHA in the message, which is what makes this ledger
auditable. A commit already present here auto-merges to an empty diff, so a
speculative cherry-pick is a cheap way to test whether something is missing.

Measured divergence, 2026-08-30: 319 shared paths, 63 byte-identical,
164 diverged (29 at ten diff lines or fewer, 50 between eleven and fifty).
Normalising the product identifiers barely moves those numbers, so the
divergence is real product logic, not naming.

## Sync State

| Direction | Last reviewed | Head reviewed |
| --- | --- | --- |
| MirrorShift to here | 2026-08-30 | `mirrorshift/main` at `0c5b593` |
| Here to MirrorShift | 2026-08-30 | `main` at `1f91848` plus the working tree |

## Already Present Here

Reviewed against `mirrorshift/main` at `0c5b593`; no action needed.

| MirrorShift | Subject | Note |
| --- | --- | --- |
| `f6860c9` | Harden Spectranext DIRECT transport | Landed here in `1f91848`; `src/spectrum/overlay/direct_ovl.c` is identical. |
| `0c5b593` | Stop truncating the overlay recipe | Landed here in `1f91848` as `tools/build_overlays.sh`. |
| `1ce7d23` | Skip null memcpy in Direct ACK detail | Already guarded at `src/common/session/direct_session.c:318`. Cherry-pick auto-merges to an empty diff. |
| `813ae52` (session part) | Session end reasons | Done here independently in `bd70c8a` with `end_reason` plus `session_emit_end`; that shape is the better one. |
| `8045025` (helpers part) | Shared text helpers | `session_text_equal` and friends already exist and are used 82 times. |
| `aaecfcf` (board part) | `draw_board_clean` / `mark_mode` | Present in `asm/spectrum/screen.asm`; this one travelled the other way. |
| `1fff4f6`, `7833cef` (setup parts) | Endpoint editing and JOIN room preservation | Ported deliberately to the existing row-masked reducer: SELECT opens editable endpoints, valid JOIN+MQTT rooms survive GAME/LINK changes, and empty suffixes auto-enter the four-character editor. NetChessZX keeps its `NC` hexadecimal room format and chess-specific config ownership. |
| `1fff4f6` (SAVE transition) | SAVE success/failure state | Already equivalent in `session_setup_save` plus TIME_CONFIG init: success produces clean `EDIT/START` with START focused; failure keeps dirty `SAVE/START` with SAVE focused; both retain the complete visible menu. Covered here by the target TIME_CONFIG vector. |

## Rejected

| MirrorShift | Subject | Why not |
| --- | --- | --- |
| `138673e` (app.c part) | Accept DIRECT GAME START without peer ready | Breaks parity. The canonical reducer NACKs a DIRECT GAME START that arrives before the peer HELLO (`src/common/session/direct_session.c:1041`), so accepting it in the compact FSM alone is a target-specific semantic exception, which `.mex/patterns/change-protocol-session.md` forbids. It also treats a transport defect as a protocol rule: on the cartridge the HELLO goes missing because DIRECT is not drained between overlay calls, which is the gap tracked below. |
| `8045025` (SNTP part) | Remove the host SNTP copy | MirrorShift has no SNTP fallback to preserve. This product does: `src/spectrum/overlay/time_ovl.c` needs it while the Next RTC path stays unvalidated. |
| `813ae52` (`fat_timezone.h`) | Shared FAT timezone helper | The conversion in `src/spectrum/overlay/time_ovl.c:31` is the better one: it handles the 2100 non-leap year and the FAT year bounds, neither of which the MirrorShift helper covers. Its unit test is still worth taking; the helper is not. |
| `142c663` | `SPXN_XFS_SCRATCH_PRESERVE` for piece masks | MirrorShift stages live piece masks at `0x662b`, inside the XFS directory scratch. This tree does not: `asm/esxdos/overlay_loader.asm` has no `piece_sprite_addr`, and `SPXN_XFS_SCRATCH_PRESERVE_SIZE=0` in the `Makefile` is correct here. |
| `tests/tools/test_setup_flow.py`, `tools/check_sdcc_iy_contract.py` | Emulated setup and ABI probes | Not needed. MirrorShift puts its z88dk-ticks probes inside two large Python files (903 and 1104 lines). The same technique already lives here as nine standalone vectors under `tests/spectrum/*_vector.asm` (2926 lines) driven by `tests/tools/test_spectrum_asm_vectors.py`. Extend those instead of importing a second harness shape. |
| `af9dde0`, `b365dcd`, `d523871` | Checkers, reversi, disc rendering | Product-specific. |

## Owed To MirrorShift

MirrorShift has `netchesszx` as a remote, so the same cherry-pick flow works
from there. Evidenced candidates, none sent yet.

1. **The DIRECT edit-line bounds vector**
   (`tests/spectrum/setup_menu_render_vector.asm` plus
   `assert_edit_line_within_buffer` in
   `tests/tools/test_spectrum_asm_vectors.py`). MirrorShift carries the same
   exact-fit buffer, `DEFS 30` at `entry_menu_config.asm:1231` with the
   15-character host clamp, and nothing guards it there.
2. **The timezone conversion** in `src/spectrum/overlay/time_ovl.c:31`.
   MirrorShift's `src/spectrum/transport/fat_timezone.h` misses the 2100
   non-leap year and the FAT year bounds. Its unit test
   (`tests/spectrum/test_fat_timezone.c`) is worth taking in exchange.
3. **The `end_reason` shape** from `bd70c8a`: one `session_emit_end` helper
   against MirrorShift's `direct_emit_end` that patches the previous action
   in place. Cosmetic; both work.
4. **The PORT auto-entry fix** in `asm/overlay/setup/entry_setup.asm`:
   call `su_room_editable` for every candidate row and return
   `_setup_port_text` for row 3. MirrorShift still checks only row 2 and its
   PORT branch leaves `HL` stale, so selecting DIRECT cannot auto-edit an empty
   port reliably there.

## Overlay-Resident Placement, 2026-08-30

`spxf_replace_atomic` belongs in the CONFIG and SAVELOAD overlays, not in the
resident. Linking it resident costs 349 bytes and breaks the stack floor here:
the Spectranext SP gap is 588 bytes against a 512-byte floor, so this tree has
76 bytes of headroom and the helper needs 352. Measured, and then corrected, in
one sitting; recorded so nobody repeats it.

That placement is the whole reason the driver split exists. SpectraNext
`1506683 feat(driver): split atomic replace helper` landed 2026-08-28, the same
day MirrorShift adopted it in `021c09f`. A standalone `spxf_replace.asm` linked
with `spxn_rom.asm` pulls neither `spxf.c` nor its handle state, which is what
makes 349 bytes small enough to sit inside a 2048-byte overlay slot
(`driver.md:104`, `storage.md:219`).

MirrorShift wires it that way and pays nothing resident:

```text
Makefile:385            SPXN_ATOMIC_OBJ := $(BUILD_DIR)/spxf_replace_ovl.o
build_overlays.sh:102   ... saveload_ovl.o ${SPXN_ATOMIC_OBJ} ...
build_overlays.sh:126   ... config_ovl.o   ${SPXN_ATOMIC_OBJ} ...
```

One copy per slot. MirrorShift's Spectranext CONFIG sits at 2039/2048 *with*
the helper already inside, so the slot does hold it. This tree now does the
same. Two consumers means two copies; if a third overlay ever needs it, weigh
a resident copy against the recovered slot space then, not before.

Built and measured here 2026-08-30 with the overlay placement:

| | Baseline | Atomic replace, resident | Atomic replace, overlays |
| --- | --- | --- | --- |
| SP gap | 588 | 236 (floor breach) | **585** |
| CONFIG slot | | | 1842 / 2048 |
| SAVELOAD slot | | | 1584 / 2048 |

The three lost bytes are the cold-boot `netchesszx_hinted_rows` clear, not the
helper, which costs the resident nothing. `_spxf_replace_atomic` no longer
appears in `build/spectranext/SHATRANJ.map` at all. The 768-byte SP warning is
pre-existing: the baseline sat at 588, also under it.

## Pending

Ranked. Nothing here is started.

1. **Spectranext size gate**. `z80opt.toml` has no `[targets.spectranext]`
   section, so the cartridge resident grows without a tripwire. MirrorShift
   pins 35822 resident and 513 SP gap. The number here has to come from a
   measured Spectranext build; do not copy MirrorShift's.
2. **Spectranext in the repository gates**. `full-check` is
   `module-guards test abi-check size-check nex-size-report`, so
   `spectranext-port-build` never runs. No workflow links the cartridge driver
   either; MirrorShift's `ci.yml` checks out `IgnacioMonge/SpectraNext` and
   runs `make tap-spectranext`.
3. **DIRECT background drain on the cartridge** (MirrorShift `021c09f`,
   `src/spectrum/transport/spectranext_direct_stage.c`).
   `src/spectrum/transport/net.c:133` states the current decision: DIRECT is
   drained only by its overlay, and the cartridge is expected to buffer while
   resident code runs. MirrorShift stages one recv in low RAM instead. Needs
   hardware evidence before porting; it is the suspected root cause of the
   dropped HELLO behind the rejected `138673e`.
4. **Resident recovery** (MirrorShift `4a9fc6d` and `f9796ce`, 282 bytes:
   33 from deduplicating the send, presence and poll helpers, 249 from sharing
   handler epilogues through goto stubs). `src/spectrum/app/app.c` has diverged,
   so port the technique and measure here, not the diff.
5. **`align_notice_text`** (MirrorShift `aaecfcf`). Replaces
   `clear_notice_row` plus `calc_len64` at `asm/spectrum/screen.asm:641` with
   one `cpir`, `lddr` and pad in place.

## Known Divergence, Not Scheduled

The canonical reducer answers a DIRECT GAME START received before the peer
HELLO with `NACK GAME START BAD` (`src/common/session/direct_session.c:1041`).
The compact FSM stays silent and shows the wait-for-opponent notice
(`src/spectrum/app/app.c:3202`). The same asymmetry exists for a HOST that
receives GAME START: the reducer sends `NACK GAME START HOST`, the FSM returns
handled.

Neither path is reachable over a healthy TCP stream, because HELLO always
precedes GAME START on the same connection, which is why no transcript covers
either one. They become reachable exactly when the transport drops bytes, which
is pending item 3. Aligning the FSM on the reducer costs resident bytes on a
target that cannot be size-checked without a Spectrum build, so it stays
recorded rather than fixed. Do not resolve it by relaxing the reducer.
