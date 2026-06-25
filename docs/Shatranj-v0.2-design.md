# Shatranj v0.2 Design

Source inputs:

- `C:\Users\ignac\Downloads\ZXChess-propuesta.md`, v0.1, 2026-05-14.
- Technical review pasted in console, 2026-05-15.
- External checks done 2026-05-15 for MQTT, Mosquitto, OCI, Ubuntu, Hetzner,
  ESP8266 AT SSL notes, and perft reference data.

## Verdict

Project viable. Core idea stays: two Spectrums make outbound TCP connections to
one MQTT broker. This fits NAT/CGNAT, ESP8266 AT limitations, and tiny chess
traffic.

v0.1 is good as PoC prose, not as implementation contract. v0.2 hardens three
areas before code:

- Reconnection and authoritative game state.
- Public broker abuse limits and plain-TCP security boundary.
- Full chess rule validation before UI polish.

Expected effort for robust v1: 160-220 hours, not 114 hours, unless transport
reuse proves nearly drop-in and the rules module passes perft early.

## Non-Goals for v1

- No chess AI.
- No ranking, accounts, or anti-cheat beyond legal move validation.
- No web spectator in v1.
- No TLS from Spectrum client.
- No triple repetition on 48K unless later memory budget proves cheap.

## Transport

Target: MQTT 3.1.1 over plain TCP port 1883.

Client session policy:

- `CleanSession=1`.
- QoS 1 only.
- Retained `meta` and `state` rebuild local state after reconnect.
- No reliance on broker offline queues.
- Client-generated packet IDs; duplicate handling at app level via ply.

Implemented MQTT packets:

- CONNECT / CONNACK
- PUBLISH / PUBACK
- SUBSCRIBE / SUBACK
- PINGREQ / PINGRESP
- DISCONNECT

Rejected:

- QoS 2 packets: PUBREC, PUBREL, PUBCOMP.
- UNSUBSCRIBE for v1.
- MQTT 5 features.

## Topic Layout

All topics have exactly four levels, so one simple ACL wildcard covers them:

```text
netchesszx/v1/<code>/meta
netchesszx/v1/<code>/state
netchesszx/v1/<code>/w2b
netchesszx/v1/<code>/b2w
netchesszx/v1/<code>/ack_w
netchesszx/v1/<code>/ack_b
netchesszx/v1/<code>/pres_w
netchesszx/v1/<code>/pres_b
```

Topic semantics:

| Topic | Retain | QoS | Writer | Purpose |
|---|---:|---:|---|---|
| `meta` | yes | 1 | host | setup, nicks, time control |
| `state` | yes | 1 | side that accepted latest move | authoritative snapshot |
| `w2b` | no | 1 | white | commands sent by white |
| `b2w` | no | 1 | black | commands sent by black |
| `ack_w` | no | 1 | black | ACKs for white moves |
| `ack_b` | no | 1 | white | ACKs for black moves |
| `pres_w` | yes | 1 | white / LWT | white presence |
| `pres_b` | yes | 1 | black / LWT | black presence |

LWT is never published to `state`. Each client uses its own `pres_*` topic as
Will topic.

## Payload Grammar

ASCII line payloads, no JSON. Session fields are space-delimited. Chat text is
the remaining line after `CHAT `. Nicks are sanitized to uppercase
`[A-Z0-9_-]`, max 12 chars.

Version appears in setup/control messages. Ply appears on moves and app ACKs.

```text
H <host_color> <session_id>
J <session_id>
META 1 <white_nick> <black_nick> <base_ds> <inc_ds> <start_hash>
GAME START
MOVE <ply> <move> [notation]
ACK <ply>
NACK <ply> <reason>
CHAT <text>
RESET
ACK RESET
PING
ACK PING

O <color> <session_id>
F <color> <session_id>
```

Examples:

```text
H W 49231
J 49231
META 1 NACHO PEPE 3000 0 STARTPOS
GAME START
MOVE 1 e2e4 e4
ACK 1
CHAT good move
F B 49231
```

First move is `ply=1`.
Only the host sends `GAME START` or `RESET`; guests acknowledge host reset with
`ACK RESET`.

`move` format is long coordinate notation:

- `e2e4`
- `e7e8q`
- promotion suffix: `q`, `r`, `b`, `n`

## App ACK Contract

MQTT PUBACK only confirms broker-level QoS flow. It does not mean the opponent
validated or applied the move.

White move flow:

1. White validates local move and publishes `MOVE 17 d1h5 Qh5` to `w2b`.
2. White marks move pending.
3. Black receives, rejects duplicates/gaps by ply, validates legality.
4. Black applies move.
5. Black publishes `ACK 17` to `ack_w`.
6. White clears pending when `ACK 17` arrives.

No client may accept a second own move while an earlier own move is pending.

## Reconnection Authority

`state` retained is source of truth.

Policy:

- Connected and own turn: accept move normally.
- Disconnected and own turn according to last `state`: allow one tentative move.
- On reconnect: resubscribe, receive retained `state`, rehydrate.
- If retained ply matches tentative base ply: publish tentative move.
- If retained ply advanced or position differs: discard tentative move and show
  real state.
- Never queue multiple own moves.

This avoids ambiguous local queues after WiFi drops.

## Pairing Code

PoC can keep 6 pronounceable chars.

v1 public should use 8 pronounceable chars plus one checksum char. UI may show:

```text
KATEMUNO-7
```

Topic code uses one MQTT level, so internal topic token is:

```text
KATEMUNO7
```

Host still checks retained `meta`/`state` before publishing, but this is not
atomic. Collision risk is accepted for casual play.

## MQTT Parser Hardening

Parser accepts untrusted bytes. Required from first commit:

- Reject MQTT remaining length over `MQTT_PACKET_MAX`.
- Reject malformed VLI: four bytes consumed and continuation bit still set.
- Validate topic length before reading topic.
- Validate QoS bits from fixed header.
- Drop QoS 2 PUBLISH; do not try to process.
- Send PUBACK only after PUBLISH topic/payload parse succeeds.
- Never copy payload unless destination capacity checked.
- Enforce app payload max separately from MQTT packet max.

Initial constants:

```c
#define MQTT_PACKET_MAX 512
#define NETCHESSZX_PAYLOAD_MAX 192
#define NETCHESSZX_TOPIC_MAX 40
```

Broker may allow `max_packet_size 1024`; client remains stricter.

## Broker v0.2 Config

Lab/public-demo baseline:

```conf
listener 1883 0.0.0.0
allow_anonymous true

persistence true
persistence_location /var/lib/mosquitto/

max_connections 100
max_inflight_messages 1
max_queued_messages 20
message_size_limit 512
max_packet_size 1024
max_qos 1

acl_file /etc/mosquitto/netchesszx.acl

log_dest file /var/log/mosquitto/mosquitto.log
log_type error
log_type warning
log_type notice
```

ACL:

```conf
topic readwrite netchesszx/v1/+/+
```

For v1 public, prefer a shared username/password over anonymous access, even
over plain TCP. It is not confidentiality; it only reduces casual abuse and bot
noise.

Plain TCP security boundary:

- Anyone on path can read/modify traffic.
- Broker operator can read all traffic.
- No private data goes in payload.
- Cheating prevention is out of scope.

## Infrastructure

OCI Always Free remains viable for development and demos:

- Ampere A1 free allowance: 4 OCPU / 24 GB RAM equivalent.
- Always Free block volume allowance: 200 GB.
- Idle Always Free instances may be reclaimed after 7 days below Oracle idle
  thresholds.

Therefore wording is:

```text
0 EUR/month target, with low-cost VPS fallback.
```

Do not promise "0 EUR/month guaranteed".

As of 2026-05-15, Hetzner CAX11 reference should not use old 3.79 EUR/month
wording; official 2026 price adjustment lists CAX11 at 4.49 EUR/month before
VAT for Germany/Finland.

For a fresh Ubuntu server:

- Ubuntu 24.04 LTS is conservative.
- Ubuntu 26.04 LTS is already released and supported to May 2031 standard
  security maintenance, but wait for provider image maturity if OCI templates
  lag.

## Web Spectator Boundary

v2 only.

Do not expose raw public port 8083 and call it done.

v2 shape:

```text
Spectrum clients -> TCP MQTT :1883
Web page         -> HTTPS
Browser MQTT     -> WSS reverse proxy -> local Mosquitto websockets listener
```

Caddy/Nginx terminates TLS. Mosquitto WebSocket listener can stay local/private.

## Chess Rules Module

Board representation: classic 10x12 mailbox, not 12x10.

Piece bytes:

```c
#define EMPTY       0x00
#define OFFBOARD    0x7F
#define BLACK       0x80
#define TYPE_MASK   0x78

#define PAWN        0x08
#define KNIGHT      0x10
#define BISHOP      0x18
#define ROOK        0x20
#define QUEEN       0x28
#define KING        0x30
```

No temporary state in piece bits. Keep transient chess state in position fields:

```c
typedef struct {
    uint8_t board[120];
    uint8_t side_to_move;
    uint8_t castle_rights;
    int8_t ep_square;
    uint8_t halfmove_clock;
    uint16_t fullmove_number;
} netchesszx_position_t;
```

Required legal-rule support:

- Legal move generator via make/unmake and own-king-in-check filtering.
- Castling, including attacked transit squares.
- En passant, including discovered self-check.
- Promotion with capture.
- Checkmate and stalemate.
- 50-move rule.
- Insufficient material.

Triple repetition:

- 48K v1: omit unless memory budget proves cheap.
- 128K/Next: optional later via history/hash.

## Validation Gate

Transport now comes first. Rules engine must pass before chess UI integration,
but not before the initial Spectrum-PC link:

- Initial position perft 1-5.
- Kiwipete perft 1-4 minimum, 1-5 if PC time acceptable.
- Special fixed tests for castling through check, moved rook/king castling
  rights, en passant self-check, promotion capture, stalemate, mate, 50-move,
  insufficient material.

Perft ignores repetition, 50-move, and insufficient-material draw rules; those
need separate tests.

## References Checked

- MQTT 3.1.1: https://docs.oasis-open.org/mqtt/mqtt/v3.1.1/os/mqtt-v3.1.1-os.html
- Mosquitto config manual: https://mosquitto.org/man/mosquitto-conf-5.html
- OCI Always Free: https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm
- ESP8266 AT SSL memory note: https://www.espressif.com/sites/default/files/4a-esp8266_at_instruction_set_en_v1.5.4_0.pdf
- Ubuntu release cycle: https://ubuntu.com/about/release-cycle
- Hetzner 2026 price adjustment: https://docs.hetzner.com/general/infrastructure-and-availability/price-adjustment/
- Chessprogramming perft results: https://www.chessprogramming.org/Perft_Results
- Chessprogramming mailbox: https://www.chessprogramming.org/Mailbox
