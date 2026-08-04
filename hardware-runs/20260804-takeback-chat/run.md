# Classic + Next takeback chat validation — 2026-08-04

Run id: 20260804-takeback-chat
Date/time/timezone: 2026-08-04, time not recorded, CEST / Europe-Madrid
Operator: Ignacio Monge García
Git state: base `232e81558080d76200441c1717c04498ce968230` plus the
uncommitted takeback-chat working-tree change

## Artifacts

| Artifact | Path | Bytes | SHA-256 |
|---|---|---:|---|
| Classic TAP | `release/SHATRANJ.tap` | 34737 | `e36067147d2f00ea205fc7856f7637f40782603e5c52ce44de36b00043d5524e` |
| Classic overlay | `release/SHATRANJ.OVL` | 22869 | `3f533cb95dba37cc0e0e0541752662cce14185ec9713973feb9e2365bcb3dbca` |
| Classic data | `release/SHATRANJ.DAT` | 2670 | `7eae7b02c62582ad8b2c727b2434a621fc078c3938c10748ea2fb4836ed18a3b` |
| Next NEX | `release/Next/SHATRANJ.nex` | 82432 | `508e8922d925a4c5f6ca5faf842a6506171a51e159c589f1d6d2ad1fe0cde004` |

## Result

| Scenario | Classic | Next | Repetitions | Evidence | Result |
|---|---|---|---:|---|---|
| Accepted TAKEBACK appears in the chat log | PASS | PASS | At least 1 each | Operator observation on physical hardware | PASS |

The transport, requester direction, exact repetition count, and captures were
not recorded, so this run proves only the accepted-takeback chat presentation
on both physical targets. The preceding software gate was `make full-check`,
which passed for the same working tree and generated artifacts.
