# Spectrum connection configuration

`SHATRANJ.CFG` stores Spectrum connection, clock, and game setup.

Classic and Next alternate atomically between `/SYS/SHATRANJ.CFG` and
`/SYS/SHATRANJ.CF2`, and retain `/SYS/CONFIG/SHATRANJ.CFG` as a read-only
legacy fallback. SpectraNext uses `/CFG/SHATRANJ.CFG`. Version 1 is a 46-byte
little-endian record:

| Offset | Size | Value |
| ---: | ---: | --- |
| 0 | 4 | `SHCF` magic |
| 4 | 1 | version (`1`) |
| 5 | 1 | record length (`46`) |
| 6 | 1 | bit 0 JOIN, bit 1 MQTT; remaining bits reserved |
| 7 | 1 | packed COLOR, NOTATION, BOARD, SET, and HINTS choices |
| 8 | 1 | active timezone (`-11..+13`, or `127` for RTC) |
| 9 | 1 | last numeric timezone for RTC fallback |
| 10 | 2 | DIRECT port |
| 12 | 17 | zero-terminated MQTT room (`NC` + four uppercase hexadecimal characters) |
| 29 | 16 | zero-terminated DIRECT host IPv4 text |
| 45 | 1 | CRC-8 polynomial `0x07` over bytes 0..44 |

Load validates magic, version, exact size, CRC, reserved bits, timezone,
game-option ranges, port, string bounds, the active MQTT room, and the active
DIRECT JOIN IPv4 before changing live state. Missing, invalid, truncated, or
oversized files use compiled defaults without partially applying the record.

For JOIN+MQTT, `NC` is fixed and cannot receive the cursor. The editor starts
on the first of the four following characters, accepts `0`-`9` and `A`-`F`
(normalizing lowercase), and requires all four before confirming. Selecting MQTT preserves an existing valid
room; an empty or invalid room becomes `NC` plus an empty suffix and enters the
editor. Selecting any editable endpoint opens it even when its displayed value
is valid. Selecting DIRECT with an empty port enters the PORT editor.

The Spectrum Setup screen presents CONNECTION SETUP first. `SAVE` writes role,
transport, endpoint, clock source, COLOR, NOTATION, BOARD, SET, and HINTS;
`EDIT` returns to those fields. Changing any persisted choice marks the record
dirty and refreshes the action row. A successful SAVE keeps the complete menu
visible, changes the action to `EDIT/START`, and focuses START. A failed SAVE
keeps `SAVE/START` with SAVE focused so it can be retried or skipped with START.

Setup rendering is row-masked: normal navigation repaints only the old and new
logical rows, while TIME and ACTION have independent UI flags. Endpoint changes
repaint only GAME/LINK/IP/PORT and the conditional COLOR row. Theme chips keep
their own colours; focus keeps Classic BRIGHT and adds a leading `|`; BOARD
theme chips also keep their four-pixel underline.
JOIN-DIRECT presents IP and PORT as two choices on one row: horizontal arrows
move focus and SPACE/ENTER opens editing, with disjoint attribute spans that do
not recolour the `:` separator. Confirming HINTS reveals SAVE/START immediately.
CONFIG aliases the Setup workspace, so SAVE reinitializes the complete Setup
state after committing or failing as described above.

`TIME` accepts UTC offsets from `-11` through `+13`, or RTC. Next uses the
NextZXOS RTC path, Spectranext uses the cartridge clock path, and Classic probes
the esxDOS driver API, `M_GETDATE`, then the DivTIESUS PCF8563 I2C device. If
RTC is unavailable, every target falls back to the last numeric UTC offset
stored beside the RTC selection. Cold boot prefers RTC whenever the hardware
probe succeeds; the TIME row still exposes UTC so the user can select the saved
numeric fallback explicitly. Emulator success does not replace physical RTC/I2C
validation.
Arrows switch the focused time source without opening the UTC editor; only
SPACE/ENTER starts editing, and other keys remain inert until then.
Classic and Next cold preflight show `CLOCK WAIT` while the RTC probe and SNTP
fallback run, followed by `CLOCK OK` or `CLOCK FAIL`. Spectranext performs its
clock synchronization without adding those UART-panel lines.
Changing between numeric UTC offsets rebases a valid resident clock locally;
it performs no SNTP I/O. If cold SNTP failed and the clock is still invalid,
Setup retries cooperatively, one transport poll per idle frame, and cancels the
attempt on START; the retry paints no clock-status message over Setup.
