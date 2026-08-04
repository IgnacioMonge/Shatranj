# Classic + Next release smoke test — 2026-08-04

Run id: 20260803-zx-next-regression
Date/time/timezone: 2026-08-04 08:00–08:30 CEST / Europe-Madrid
Operator: Ignacio Monge García (hardware) and Codex (Qt peer/log review)
Git commit: 3f8b7b8d7be3cba5fc1dcfb9a1665997c6971764

## Artifacts

| Artifact | Path | Bytes | SHA-256 |
|---|---|---:|---|
| Classic TAP | `release/SHATRANJ.tap` | 34682 | `94ad6b648709c18ca0e65ba4d984b57e84e1a0068a04430c8bcd0be8362282eb` |
| Classic overlay | `release/SHATRANJ.OVL` | 22869 | `96345416bba7ac18c4b0c61ed204946d5dd507c3059bc2e86b14c8cbf243f32c` |
| Classic data | `release/SHATRANJ.DAT` | 2670 | `7eae7b02c62582ad8b2c727b2434a621fc078c3938c10748ea2fb4836ed18a3b` |
| Next NEX | `release/Next/SHATRANJ.nex` | 82432 | `50b48eee8685848b29f9ac2d4ad2c8f5f0050aa9b195eefaad1bb204ab4103c2` |
| Tested macOS client executable (superseded test build) | Not retained | 604160 | `87b96fe7c10f2add26b4206b261b64ed42c26c111ef3e06b965bbde06819e8e4` |
| Repackaged macOS release candidate | `build/qt-client/shatranj-client.app/Contents/MacOS/shatranj-client` | 604160 | `e3da8fcd6db2bbeab94682399b3786af342dd08ad0b0d8a28769f3951a9618ae` |

## Target and transport metadata

- Classic target: physical 48K ZX Spectrum, `192.168.0.200`, TAP/OVL/DAT.
- Next target: physical ZX Spectrum Next, `192.168.0.124`, self-contained NEX;
  core/version not recorded.
- ESP AT firmware: project target 1.7.6; device/version observed: PENDING.
- Classic UART backend: DIVMMC/divTIESUS; exact physical route and electrical
  measurements not recorded.
- Next UART backend: internal UART; exact core and electrical measurements not
  recorded.
- Qt peer: macOS, `192.168.0.199`.

## Scenarios

| Scenario | Classic | Next | Repetitions | Log/capture refs | Result |
|---|---|---|---:|---|---|
| Boot current release artifacts | PASS | PASS | 1 each | Operator observation | PASS |
| DIRECT: Spectrum host → Qt guest | PASS | Not run | 1 | Qt log reviewed live | PASS |
| DIRECT: Qt host → Spectrum guest | Not run | PASS, port 5001 | 1 | Qt log reviewed live | PASS |
| MQTT: Qt host → Spectrum guest | Not run | PASS, HiveMQ room `NC6C9C` | 1 | Qt log reviewed live | PASS |
| START and one MOVE per side | PASS | PASS in DIRECT and MQTT | 3 sessions | Qt log reviewed live | PASS |
| CHAT in both directions | PASS | PASS in DIRECT and MQTT | 3 sessions | Qt log reviewed live | PASS |
| Clean BYE/disconnect | PASS | PASS in DIRECT and MQTT | 3 sessions | Qt log reviewed live | PASS |
| MQTT Qt disconnect/reconnect while Next remains in room | Not run | PASS repeatedly; count not recorded | Multiple | Operator observation | PASS |
| Palette, piece sets, About, and settings sweep | PENDING | PENDING | 0 | None | PENDING |
| DRAW, RESET, RESIGN, RESTORE, and liveness expiry | PENDING | PENDING | 0 | None | PENDING |
| TAKEBACK end-to-end | PENDING | PENDING | 0 | None yet | PENDING |
| Reconnect timing calibration | PENDING | PENDING | 0 | None yet | PENDING |
| Dirty-link loss | PENDING | PENDING | 0 | None yet | PENDING |
| Next ESP hard-reset recovery | PENDING | PENDING | 0 | None yet | PENDING |

An initial MQTT reconnect anomaly used an older Next binary and is excluded
from release-candidate evidence. After loading the NEX hash listed above, every
observed Qt reconnect established a stable session. This was a bounded release
smoke test, not the exhaustive matrix represented by the remaining `PENDING`
rows.
