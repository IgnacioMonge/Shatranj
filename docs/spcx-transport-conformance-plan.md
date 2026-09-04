# SPCX Transport Conformance Plan

Status: deterministic implementation and FuseX soak complete on
`test/spcx-transport-conformance`; physical evidence is tracked separately
below.

## Objective

Prove that the Spectranext socket adapter preserves the existing DIRECT
transport and session contracts across idle time, fragmented I/O, readiness
flags, backpressure, liveness, closure, and reconnection.  The suite must catch
the empty-poll busy-loop regression without adding a third session-policy
implementation.

## Preserved Behaviour And Limits

- `docs/wire-contract.md` and `docs/session-core-contract.md` remain unchanged.
- ESP/UART and SPCX move bytes differently but expose the same application
  payloads and bounded liveness frontier.
- Session policy remains in the canonical and compact reducers; transport tests
  observe mechanics only.
- No production dependency, heap use, resident state, or new overlay entry.
- No emulator result is reported as real-hardware evidence.
- The task has one build command.  All compilable checks are aggregated before
  that command is spent.

## Acceptance Criteria

1. A scripted empty SPCX poll performs exactly one explicit frame yield, reads
   no data, and reports timeout.  Wall-clock cadence is measured separately
   because the cartridge call itself is outside the host seam.
2. Scripted receive/send results cover fragmentation, readiness plus closure,
   would-block, fatal error, peer close, and backpressure without byte loss or
   false link loss.
3. Keepalive tests prove delayed `ACK PING`, bounded silent-peer loss, and
   counter-boundary behaviour using deterministic time rather than wall time.
4. A closed active socket can be replaced by a fresh listen/accept/connect
   cycle without inherited peer/session state.
5. One focused command compiles and runs the complete deterministic suite.
6. The automated network side of a black-box PC-to-FuseX soak survives at least
   15 minutes and multiple keepalive windows, performs one fresh connection,
   records machine-readable evidence, and owns no emulator process.
7. A hardware smoke protocol records artifact hashes, roles, timings, core and
   firmware.  Its result remains `PENDING` until executed on physical hardware.

## Option Ledger

| Option | Cost / saving | Risk | Decision and proof |
| --- | --- | --- | --- |
| Extend the existing SPCX host seam | Test-only code; reuses fakes and production entry points | May miss full-process integration | Do; deterministic mechanics gate |
| Reuse shared session transcripts | Zero new policy model | Does not exercise socket adapter | Do for semantic/liveness boundaries only |
| Add a production transport abstraction | Resident/overlay bytes, calls and maintenance | Creates a third decision surface | Reject |
| Add a table-driven host model | Test-only data and fast execution | Expected results could drift | Do only where expectations cite the contracts or ESP behaviour |
| Add black-box FuseX soak tooling | Host-only time/process cost | Emulator is not hardware | Do after deterministic gate |
| Assert GUI pixels or scrape logs | Brittle and presentation-dependent | False failures, weak transport evidence | Reject |
| Record a physical smoke run | Human/device time; strongest timing evidence | Cannot be automated without the device | Specify and execute when hardware is accessible |

## Coverage Matrix

| Case | Deterministic seam | Shared judge | FuseX soak | Hardware |
| --- | ---: | ---: | ---: | ---: |
| Empty poll / one-frame yield | Required | N/A | Observed | Timed |
| Complete and fragmented RX | Required | Payload outcome | Observed | Smoke |
| Readable plus close/error flags | Required | Link outcome | Observed | Smoke |
| Would-block versus fatal error | Required | Link outcome | N/A | N/A |
| Full, partial, and blocked TX | Required | TX-result semantics | Observed | Smoke |
| Delayed `ACK PING` | Scripted time | Liveness outcome | Required | Timed |
| Silent peer deadline | Scripted time | ENDED outcome | Optional destructive case | Timed |
| Counter boundary/wrap | Required | Liveness outcome | N/A | N/A |
| Close, listen and reconnect | Required | Fresh-session outcome | Required | Required |

## Execution Plan

### Phase 1 — Contract map and ownership

- Trace ESP/UART and SPCX read, send, wait, close, listen and accept paths.
- Bind every expected result to the wire/session contract or existing ESP
  behaviour.
- Assign one mutable owner per test/tool file and freeze production code unless
  a new failing case proves a defect.

Gate: reviewed matrix with no target-specific session expectation.

### Phase 2 — Deterministic transport suite

- Extend the current SPCX link seam with scripted poll/recv/send outcomes.
- Add the smallest reusable case table needed to compare pacing and error
  classification.
- Exercise real production adapter functions; mocks replace only platform I/O
  and frame waiting.

Gate: every case fails for its deliberately broken seam and passes for current
production behaviour; no product-size impact.

### Phase 3 — Liveness and reconnection

- Reuse the existing shared transcript judge for policy outcomes.
- Add adapter-level frame/tick assertions around the compact DIRECT watchdog.
- Cover delayed ACK, silent peer, boundary counters, active close and a fresh
  accepted connection without resuming discarded state.

Gate: canonical and compact outcomes agree; adapter timing stays mechanical.

### Phase 4 — Black-box FuseX soak

- Stage only the current accepted production artifacts; the deterministic host
  gate does not rebuild product media.
- Launch SPCX through the existing ZXESPEmu/FuseX contract.
- Drive or observe a DIRECT peer without relying on screenshots.
- Sample connection state and protocol traffic for at least 15 minutes, require
  survival across keepalive windows, perform one reconnect, and emit JSON
  evidence with timestamps and hashes.
- Terminate only processes created by the runner.

The existing FuseX launcher has no keyboard/control API.  Starting CREATE or
JOIN is therefore an explicit emulator UI precondition, not hidden GUI scraping
inside the network probe.  Once the listener exists, the network run is:

```text
C:/Program Files/Python311/python.exe tools/spcx_direct_conformance.py
  --mode guest --host 127.0.0.1 --port 5000 --duration 900 --require-mach
  --reconnect-attempts 1 --reconnect-after 30 --reconnect-backoff 5
  --require-reconnects 1 --artifact release/Spectranext/SHATRANJ.tap
  --artifact release/Spectranext/SHATRANJ.OVL
  --artifact release/Spectranext/SHATRANJ.DAT
  --output build/spcx-conformance/fusex-soak.json
```

Gate: stable interval, keepalive evidence, successful reconnect and clean exit.

### Phase 5 — Physical-hardware smoke

- Use the same artifact hashes and both HOST/GUEST roles.
- Record Spectrum Next core/firmware, Spectranext version, refresh rate, peer
  platform, handshake time, PING cadence, disconnect deadline and reconnect.
- Mark every case PASS/FAIL/PENDING; retain raw capture outside the repository.

Gate: physical evidence is authoritative for timing.  Lack of device access is
reported as `PENDING`, never converted to PASS.

Record at least:

```text
result: PASS | FAIL | PENDING
artifact_sha256: TAP / OVL / DAT
device: model / core / firmware / Spectranext version / refresh rate
network: peer / role / address / port
handshake: HELLO / MACH / elapsed seconds
liveness: first PING / ACK delay / silent-peer disconnect
reconnect: TCP close / new HELLO / no resumed game state
evidence: timestamp / operator / external log or photograph paths
```

### Phase 6 — Aggregate validation and handoff

- Run the single focused build/test command after batching all edits.
- Run non-building static checks, the accepted FuseX soak, `git diff --check`,
  and final status inspection.
- Report changed files, exact coverage, measured binary impact, emulator result,
  hardware result, rejected options and residual risk.

Stop: finish only when every software gate is green and every hardware item has
an honest PASS/FAIL/PENDING record.

## Execution Record — 2026-08-27

- Branch isolation: PASS.
- `make PYTHON="C:/Program Files/Python311/python.exe"
  spectranext-conformance-test`: PASS.  This was the task's only build command.
- SPCX seam, Next ping and DIRECT parity binaries: PASS.
- Python peer: 10 tests PASS in 0.059 seconds.
- Product binary impact: zero; production sources were not changed by this
  suite.
- Pre-suite regression run: PC-to-FuseX stayed established for more than 99
  seconds after the empty-poll fix, versus the former repeatable 6–7 seconds.
- New 15-minute soak: PASS.  The accepted run lasted 900.015 seconds, completed
  two HELLO/MACH handshakes, forced one close/reconnect at 30 seconds, received
  297/297 `ACK PING` replies, and recorded zero unanswered PINGs, malformed
  frames, embedded NULs, oversize frames, send failures, reconnect failures, or
  peer closes.  The peer identified as `ZX`; all TAP/OVL/DAT hashes matched.
  Evidence: `build/spcx-conformance/fusex-soak.json`.
- Physical hardware: PENDING; no device was accessible to this execution.
