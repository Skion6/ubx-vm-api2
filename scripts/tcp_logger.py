#!/usr/bin/env python3
"""
scripts/tcp_logger.py

Simple TCP listener that prints the raw bytes received (hex and printable).
Use this on the Windows host (stop Uvicorn first) to inspect the exact bytes arriving
from the VPS DNAT/tunnel.

Usage:
  python scripts/tcp_logger.py [port] [bind_addr]

Examples:
  python scripts/tcp_logger.py 8000         # listen on 0.0.0.0:8000
  python scripts/tcp_logger.py 8000 127.0.0.1

"""
import socket
import sys


def hexdump(data: bytes) -> str:
    return " ".join(f"{b:02x}" for b in data)


def printable(data: bytes) -> str:
    return "".join(chr(b) if 32 <= b < 127 else "." for b in data)


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    host = sys.argv[2] if len(sys.argv) > 2 else "0.0.0.0"

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((host, port))
        s.listen(5)
        print(f"tcp_logger listening on {host}:{port}")
        try:
            while True:
                conn, addr = s.accept()
                with conn:
                    print(f"connection from {addr}")
                    data = conn.recv(4096)
                    if not data:
                        print("<no data>")
                        continue
                    print("--- printable ---")
                    print(printable(data[:1024]))
                    print("--- hex (first 1024 bytes) ---")
                    print(hexdump(data[:1024]))
        except KeyboardInterrupt:
            print("exiting")


if __name__ == "__main__":
    main()
