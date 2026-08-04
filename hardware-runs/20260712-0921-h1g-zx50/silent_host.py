#!/usr/bin/env python3
"""H1-G peer host silencioso — sustituto del analizador logico.

Hace de host DIRECT en TCP :5000 (contrato: docs/wire-contract.md).
Completa HELLO / GAME START, hace ACK del primer MOVE del ZX (ese ACK es t0)
y despues enmudece: solo lee y cronometra cada linea entrante.

El target decide PING/teardown a ~3/18/33 s, pero este extremo TCP no observa
ni la recepcion del ACK en el ZX ni su teardown logico: sendall/FIN incluyen
latencia ESP. Por eso juzga solo lo observable aqui: exactamente 2 PING,
separados ~15 s, ningun otro trafico y cierre TCP eventual.
Tras el teardown, reconecta desde el ZX: debe llegar un HELLO DIRECT GUEST
nuevo (partida limpia, sin replay).

Uso:  py silent_host.py <n_repeticion>       (1, 2 o 3)
Log:  h1g-silent-r<n>.log junto a este script.

# ponytail: timestamps en el extremo TCP (jitter WiFi ~decenas de ms);
# tolerancia util +-0.5 s, sobra para distinguir 3/18/33 s. Si algun dia
# hace falta precision de frame real, ahi si toca sonda UART.
"""

import os
import socket
import sys
import time

PORT = 5000
PING_GAP_EXPECT = 15.0
TOL = 0.5

run_dir = os.path.dirname(os.path.abspath(__file__))
rep = sys.argv[1] if len(sys.argv) > 1 else "1"
log_path = os.path.join(run_dir, f"h1g-silent-r{rep}.log")
log_file = open(log_path, "a", encoding="utf-8")
t0 = None


def log(msg):
    delta = f"{time.monotonic() - t0:+8.3f}s" if t0 is not None else " " * 9
    line = f"[{time.strftime('%H:%M:%S')}] {delta} {msg}"
    print(line)
    log_file.write(line + "\n")
    log_file.flush()


def send(conn, payload):
    conn.sendall((payload + "\n").encode())
    log(f"TX {payload}")


def lines(conn):
    """Genera lineas \n-delimitadas; termina al cerrarse la conexion."""
    buf = b""
    while True:
        try:
            chunk = conn.recv(256)
        except socket.timeout:
            log("!! timeout de lectura (60 s sin nada) — abortando fase")
            return
        except ConnectionError:
            return
        if not chunk:
            return
        buf += chunk
        while b"\n" in buf:
            raw, buf = buf.split(b"\n", 1)
            yield raw.decode(errors="replace").strip("\r")


def accept(server, banner):
    log(f"-- esperando conexion del ZX ({banner})...")
    conn, addr = server.accept()
    conn.settimeout(60)
    log(f"-- conexion de {addr[0]}:{addr[1]}")
    return conn


server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind(("0.0.0.0", PORT))
server.listen(1)
log(f"== H1-G repeticion {rep} — host silencioso en puerto {PORT}")
log(
    "== En el ZX: DIRECT guest hacia la IP de este PC, haz UNA jugada y no toques nada mas"
)

# ---- Fase 1: handshake + primer MOVE, luego silencio ----
conn = accept(server, "fase 1: partida")
send(conn, "HELLO DIRECT HOST WHITE=GUEST")
pings = []
close_at = None
extras = []
for line in lines(conn):
    log(f"RX {line}")
    if t0 is None:
        if line == "HELLO DIRECT GUEST":
            send(conn, "GAME START WHITE=GUEST")
        elif line == "ACK GAME START":
            pass  # el ZX tiene blancas; esperamos su MOVE
        elif line.startswith("MOVE "):
            ply = line.split()[1]
            send(conn, f"ACK {ply}")
            t0 = time.monotonic()
            log(
                f">> t0 fijado (ACK {ply} enviado). Host mudo desde ahora. No toques el ZX."
            )
        continue
    # Despues de t0: solo cronometrar
    if line == "PING":
        pings.append(time.monotonic() - t0)
    elif line == "BYE":
        pass  # parte normal del teardown
    else:
        extras.append(line)
if t0 is not None:
    close_at = time.monotonic() - t0
    log(f">> conexion cerrada por el ZX a t0{close_at:+.3f}s")
conn.close()

# ---- Fase 2: reconexion limpia ----
fresh_hello = False
if t0 is not None:
    while not fresh_hello:
        conn = accept(server, "fase 2: reconecta desde el ZX, partida nueva")
        send(conn, "HELLO DIRECT HOST WHITE=GUEST")
        for line in lines(conn):
            log(f"RX {line}")
            if line == "HELLO DIRECT GUEST":
                fresh_hello = True
                log(
                    ">> handshake nuevo OK (sin replay). Puedes cortar aqui (Ctrl+C) o jugar."
                )
                send(conn, "GAME START WHITE=GUEST")
            elif line.startswith(("MOVE ", "ACK ")):
                break  # partida viva: suficiente evidencia
            elif line == "PING":
                send(conn, "ACK PING")
        conn.close()
        if not fresh_hello:
            log(">> socket pre-HELLO descartado; sigo esperando reconexion limpia")
server.close()

# ---- Veredicto ----
log("== RESUMEN ==")
ok = True
if len(pings) == 2:
    for i, got in enumerate(pings, 1):
        log(f"   PING {i}: TCP t0+{got:.3f}s (absoluto informativo)")
    gap = pings[1] - pings[0]
    mark = "OK" if abs(gap - PING_GAP_EXPECT) <= TOL else "FUERA DE TOLERANCIA"
    ok &= mark == "OK"
    log(f"   intervalo PING: {gap:.3f}s (esperado ~{PING_GAP_EXPECT}s) {mark}")
else:
    ok = False
    log(f"   PINGs: {len(pings)} (esperados 2) FALLO — {['%.3f' % p for p in pings]}")
if close_at is not None:
    log(f"   cierre TCP eventual: t0+{close_at:.3f}s OK (absoluto informativo)")
else:
    ok = False
    log("   teardown: no observado FALLO")
if extras:
    ok = False
    log(f"   trafico inesperado tras t0: {extras} FALLO")
log(f"   reconexion con HELLO nuevo: {'OK' if fresh_hello else 'FALLO'}")
ok &= fresh_hello
log(f"== VEREDICTO r{rep}: {'VERDE' if ok else 'ROJO'} ==")
log_file.close()
