#!/usr/bin/env python3
"""Deterministic DIRECT peer for the H4/H1 hardware gate."""

import os
import socket
import sys
import time


PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
TIMEOUT = 90
LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "control_logic_peer.log")
LOG_FILE = open(LOG_PATH, "w", encoding="utf-8")


def log(message):
    line = f"[{time.strftime('%H:%M:%S')}] {message}"
    print(line, flush=True)
    LOG_FILE.write(line + "\n")
    LOG_FILE.flush()


def send(conn, payload):
    conn.sendall((payload + "\n").encode("ascii"))
    log(f"TX {payload}")


class Peer:
    def __init__(self, conn):
        self.conn = conn
        self.buf = b""

    def receive(self):
        while b"\n" not in self.buf:
            chunk = self.conn.recv(256)
            if not chunk:
                raise RuntimeError("el Next cerro la conexion")
            self.buf += chunk
        raw, self.buf = self.buf.split(b"\n", 1)
        line = raw.decode("ascii", errors="replace").rstrip("\r")
        log(f"RX {line}")
        if line == "PING":
            send(self.conn, "ACK PING")
            return self.receive()
        return line

    def expect(self, expected):
        line = self.receive()
        while line == "HELLO DIRECT GUEST" and expected != line:
            send(self.conn, "HELLO DIRECT HOST WHITE=GUEST")
            line = self.receive()
        if line != expected:
            raise RuntimeError(f"esperado {expected!r}; recibido {line!r}")

    def expect_prefix(self, prefix):
        line = self.receive()
        while line == "HELLO DIRECT GUEST":
            send(self.conn, "HELLO DIRECT HOST WHITE=GUEST")
            line = self.receive()
        if not line.startswith(prefix):
            raise RuntimeError(f"esperado prefijo {prefix!r}; recibido {line!r}")
        return line


def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("0.0.0.0", PORT))
    server.listen(1)
    log(f"LISTEN :{PORT} — conecta el Next como DIRECT GUEST")
    conn, addr = server.accept()
    conn.settimeout(TIMEOUT)
    log(f"CONNECTED {addr[0]}:{addr[1]}")
    peer = Peer(conn)

    send(conn, "HELLO DIRECT HOST WHITE=GUEST")
    peer.expect("HELLO DIRECT GUEST")
    send(conn, "GAME START WHITE=GUEST")
    peer.expect("ACK GAME START")

    log("PASO 1 — mueve e2-e4 en el Next")
    move = peer.expect_prefix("MOVE ")
    ply = move.split()[1]
    send(conn, "RESET")
    peer.expect("NACK RESET BUSY")
    send(conn, "DRAW")
    peer.expect("NACK DRAW")
    send(conn, f"ACK {ply}")
    log("PASS H1/MOVE — RESET y DRAW rechazados; MOVE conservado")

    send(conn, "MOVE 2 e7e5")
    peer.expect_prefix("ACK 2")
    log("PASO 2A — mueve g1-f3 en el Next")
    peer.expect_prefix("MOVE 3 g1f3")
    send(conn, "ACK 3")
    log("PASO 2B — solicita TAKEBACK desde el menu del Next")
    takeback = peer.expect_prefix("TAKEBACK ")
    takeback_ply = takeback.split()[1]
    send(conn, "RESET")
    peer.expect("NACK RESET BUSY")
    send(conn, "DRAW")
    peer.expect("NACK DRAW")
    send(conn, f"ACK {takeback_ply}")
    log("PASS H1/TAKEBACK — RESET y DRAW rechazados; TAKEBACK conservado")

    log("PASO 3 — solicita RESET desde el menu del Next")
    peer.expect("RESET")
    send(conn, "RESET")
    peer.expect("NACK RESET BUSY")
    send(conn, "NACK RESET")
    log("PASS H4 — RESET cruzado en partida activa rechazado BUSY")

    log("PASO 4 — acepta DRAW y despues RESET cuando aparezcan")
    send(conn, "DRAW")
    peer.expect("ACK DRAW")
    send(conn, "RESET")
    peer.expect("ACK RESET")
    send(conn, "GAME START WHITE=GUEST")
    peer.expect("ACK GAME START")
    log("PASS REMATCH — partida nueva iniciada")
    log("VERDE H4/H1/REMATCH")

    conn.close()
    server.close()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, RuntimeError) as exc:
        log(f"ROJO — {exc}")
        sys.exit(1)
