# H1-G ZX 50 Hz — run 20260712-0921

Run id: 20260712-0921-h1g-zx50
Date/time/timezone: 2026-07-12 / Europe-Madrid
Operator: Ignacio
Git commit: 8cf81ef (Add Session Core reserve headroom)
Target artifact: release/SHATRANJ.tap / 34195 bytes / 46F0A229A77515F9F2741D47D3312D74379A6F44166A77A430832169CA9861D9
OVL: release/SHATRANJ.OVL / 25275 bytes / AD42BB79651DBDA7BE2CEC1F46634B5B571F9E62826E419447E5B468188EF24A
DAT: release/SHATRANJ.DAT / 2670 bytes / 7EAE7B02C62582AD8B2C727B2434A621FC078C3938C10748EA2FB4836ED18A3B
PC executable path, bytes, SHA-256: hardware-runs\20260712-0921-h1g-zx50\shatranj-client.exe / 481280 bytes / 77EC3BB4E2A8E5A7203B4A07401DF5A4A90F990D2A0F851A8216FD87D40B50A1
ZX model/revision and video standard: / 50 Hz
ESP model and AT firmware version: ESP8266 (ESP-WROOM-02) / AT 1.6.2.0 (Apr 13 2018), bin 1.6.2 — via NetManZX 1.4.5 MODULE INFO. NOTE: firmware AT muy antiguo (2018, NonOS SDK); sospechoso primario del RED M03 `DIRECT CMD UART` (CIPSEND/flow-control degradado tras uso prolongado; solo power-cycle recupera).
UART route, voltage and decoded baud/frame format: / 115200 8N1
Network topology and peer addresses:
Logic-analyzer model, sample rate and capture filename:
Frame-reference signal and channel:
Matching transcripts: liveness-guest-loss; restore-partial-linkdown-reconnect
Result:
Notes:
Current PC peer built Release/x64 with Ninja/MSVC outside Dropbox.  Its linked
DIRECT adapter test exits 0 (`PC direct adapter tests ok`).  Add
`C:\Qt\6.11.0\msvc2022_64\bin` to PATH when launching the unbundled executable.
A2 proves HELLO/START/MOVE over real localhost TCP followed by two 50 ms silent
windows with both endpoints connected.  No hardware result is claimed here.

## Operator commands — PowerShell 7

The preparation host has no `sigrok-cli`, PulseView or Saleae Logic executable
installed as of 2026-07-12.  Set the analyzer-specific values below after
installing the vendor package or portable sigrok build; do not guess the driver,
connection or channel names.  `sigrok-cli --driver $driverArg --show` must list
the selected three channels before connecting them to the target.

```powershell
Set-Location 'C:\Users\ignac\Dropbox\Retro\Software\Para divMMC\NetChessZX'
$run = 'hardware-runs\20260712-0921-h1g-zx50'
$peerExe = Join-Path $run 'shatranj-client.exe'
$peerHash = '77EC3BB4E2A8E5A7203B4A07401DF5A4A90F990D2A0F851A8216FD87D40B50A1'
if ((Get-FileHash -Algorithm SHA256 -LiteralPath $peerExe).Hash -ne $peerHash) {
    throw 'Wrong H1-G PC peer binary'
}
$env:PATH = 'C:\Qt\6.11.0\msvc2022_64\bin;' + $env:PATH
$peer = Start-Process -FilePath $peerExe -PassThru

$sigrok = '<absolute-path-to-sigrok-cli.exe>'
$driver = '<analyzer-driver>'
$connection = '<driver-connection-or-empty>'
$zxTxChannel = '<ch0>'
$zxRxChannel = '<ch1>'
$frameChannel = '<ch2>'
if ($sigrok -like '<*' -or $driver -like '<*' -or
    $zxTxChannel -like '<*' -or $zxRxChannel -like '<*' -or
    $frameChannel -like '<*') {
    throw 'Fill analyzer path, driver and physical channel mapping first'
}
$channels = "$zxTxChannel=ZX_TO_ESP,$zxRxChannel=ESP_TO_ZX,$frameChannel=FRAME"
$driverArg = if ($connection -and $connection -notlike '<*') {
    $driver + ':conn=' + $connection
} else {
    $driver
}
& $sigrok --driver $driverArg --show

foreach ($repeat in 1..3) {
    $capture = Join-Path $run ("h1g-zx50-r{0}.sr" -f $repeat)
    & $sigrok --driver $driverArg --config samplerate=10m `
        --channels $channels --time 45s --output-file $capture
    if ($LASTEXITCODE -ne 0) { throw "Capture $repeat failed" }
    $zxTxDecoder = "uart:rx=$zxTxChannel`:baudrate=115200:num_data_bits=8:parity_type=none:num_stop_bits=1:bit_order=lsb-first"
    $zxRxDecoder = "uart:rx=$zxRxChannel`:baudrate=115200:num_data_bits=8:parity_type=none:num_stop_bits=1:bit_order=lsb-first"
    & $sigrok -i $capture `
        -P $zxTxDecoder `
        -A uart --protocol-decoder-samplenum |
        Set-Content -LiteralPath (Join-Path $run ("h1g-zx50-r{0}-zx-tx.txt" -f $repeat))
    & $sigrok -i $capture `
        -P $zxRxDecoder `
        -A uart --protocol-decoder-samplenum |
        Set-Content -LiteralPath (Join-Path $run ("h1g-zx50-r{0}-zx-rx.txt" -f $repeat))
    & $sigrok -i $capture -O vcd `
        -o (Join-Path $run ("h1g-zx50-r{0}.vcd" -f $repeat))
}
```

For each repetition, start the 45-second capture immediately before causing the
last valid peer application payload.  Do not stop the peer or TCP connection;
after that payload it must remain silent.  Explicitly fail the run if the full
GUI client emits any spontaneous byte during a silence interval; A2 qualifies
the adapter, not the GUI timer executor.  Record the final decoded byte of the
last valid peer payload as `t0`, then count FRAME edges to the first PING,
second PING and teardown.
Keep the raw `.sr`, decoded UART text and `.vcd`; do not substitute screenshots.
Connect only through level-safe probes and record analyzer model, actual sample
rate, driver, connection and physical channel mapping in the metadata above.

## Procedure

1. Capture target-to-ESP UART, ESP-to-target UART and a level-safe frame reference at 2 MHz minimum.
2. Start a valid DIRECT game with ZX as guest/initiator.
3. Send one valid peer application payload; mark the end of its final UART byte as t0.
4. Keep TCP connected and send no more payloads or ACK PING.
5. Record the first PING, second PING and teardown.
6. Repeat three times without changing artifact, video mode or instrumentation.

## Measurements

| Repetition | First PING frame | Second PING frame | Teardown frame | UART capture | Frame capture | Result |
|---|---:|---:|---:|---|---|---|
| 1 | | | | | | |
| 2 | | | | | | |
| 3 | | | | | | |

Acceptance: never early; expected 150/900/1650 frames, each event at most two
frames late plus UART serialization. Exactly two PING payloads. Teardown must
discard the game; the next connection starts HELLO and a fresh board.
