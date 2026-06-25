# MQTT Session Policy

Current implementation target: deterministic HOST/GUEST startup over MQTT
without starting a game before both peers are visible.

## Roles

- The Spectrum MQTT build is now a single package:
  `MQTT/SHATRANJ.TAP` plus `MQTT/SHATRANJ.OVL`.
- The setup menu selects host/join at runtime.
- Only the host selects color and session id. A guest learns both from
  `H W/B <sid>` and then uses the opposite local color.
- Host publishes `H ...`; joiner publishes `J ...`.
- Move, ACK, presence, client id, and peer detection topics are selected from
  the runtime local color after the role/color handshake.

## Subscriptions

Each MQTT client subscribes to:

- incoming move topic (`w2b` or `b2w`)
- incoming app ACK topic (`ack_w` or `ack_b`)
- peer retained presence topic (`pres_w` or `pres_b`)
- shared `meta`

Own presence is published retained as:

```text
O W <sid>
O B <sid>
```

Host publishes retained setup as color/config hint:

```text
H W <sid>
H B <sid>
```

Joiner publishes live join setup:

```text
J <sid>
```

## Peer Ready

A retained payload never proves that the peer is alive. Retained `HOST` is
ignored as authoritative setup; the guest waits for a live host setup.

A client marks the peer ready only from live role-complementary messages:

- host receives live `J <sid>`
- guest receives live `H <color> <sid>`

After a host receives live `J ...`, it republishes `H ...` live on `meta`
as an acknowledgement so the guest can leave `Waiting host`.

`O <opponent_color> <sid>` is soft presence only. It can update status,
but it must not set peer-ready because retained presence may be stale.

Own retained `HOST`, own retained `ONLINE`, retained `JOIN`, and own repeated
`JOIN` are ignored for peer-ready.

## Disconnect

Presence is retained:

```text
O W <sid>
O B <sid>
F W <sid>
F B <sid>
```

MQTT clients publish retained `F W/B <sid>` before a clean disconnect once
their side is known. A host additionally clears retained `meta` with an empty
retained publish so the next guest does not see stale setup.

Empty retained payloads are ignored by both clients.

## Connect Robustness

The Spectrum MQTT overlay first tries a fast `AT` probe and only resets the ESP
if command mode cannot be recovered. TCP/MQTT session open is retried once after
returning to command mode and re-preparing the single-link settings.

## Start

- A game is inactive after MQTT broker connection.
- No board move is accepted before `GAME START`.
- Only the host starts the game.
- Only the host resets the game. Guests apply host `RESET` and answer
  `ACK RESET`; hosts ignore guest `RESET`.
- A joiner pressing SPACE before `GAME START` sees `Waiting host start`.
- A host pressing SPACE before peer detection sees `Waiting peer`.
- A host with peer ready sees `Peer ready - START` on Spectrum.
- A guest with live host ready sees `Host ready - wait START` on Spectrum.
- The PC MQTT client enables Start Game only when it is the host and the peer is
  ready.
- A guest accepts `GAME START` only after a live `H <color> <sid>` has selected
  color/session and marked the host ready.

Start payload:

```text
GAME START
```

On receipt, the peer starts locally and answers with app ACK:

```text
ACK GAME START
```

MQTT `PUBACK` is never treated as game acceptance.
