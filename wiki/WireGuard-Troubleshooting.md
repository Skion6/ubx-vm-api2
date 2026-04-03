WireGuard tunnel — Troubleshooting guide
======================================

This document collects minimal steps to resolve the "Invalid HTTP request" symptom when forwarding
traffic through a WireGuard tunnel + DNAT to a backend HTTP server (Uvicorn).

Symptoms
- Uvicorn logs many: Invalid HTTP request received.
- tcpdump on the Windows host shows packets arriving.

Likely causes
- MTU / fragmentation: WireGuard overhead causes TCP segments to be fragmented or truncated.
- TCP MSS mismatch: SYN MSS does not account for tunnel overhead and later segments are broken.
- Protocol mismatch: TLS or PROXY-protocol bytes delivered to plain-HTTP listener.

Files added to this repo to help
- tools/wg_fix.sh — set MTU on a wg interface and add TCPMSS clamp on the VPS.
- tools/tcp_logger.py — run on the Windows host (stop Uvicorn first) to print the raw bytes.

Concise commands and steps

On the VPS (run as root):

sudo bash tools/wg_fix.sh wg0 1280

This sets MTU on the wg interface (if present) and adds the tcpmss clamp rule in the mangle table.

Verify forwarded packets are being seen (replace <public-if> and <windows-wg-ip>):

sudo tcpdump -nn -s 0 -A -i <public-if> host <windows-wg-ip> and port 8000

On the Windows host:

1. Edit your WireGuard peer config and add in the [Interface] section:

MTU = 1280

then restart the tunnel.

2. Stop Uvicorn and run the TCP logger to inspect the first bytes that arrive:

python tools/tcp_logger.py 8000 0.0.0.0

3. Alternatively capture traffic with Wireshark or Windump on the WireGuard interface:

windump -i <wg-if> -s 0 -A port 8000

Interpretation notes

- If the TCP logger shows readable HTTP methods (GET/POST) — networking is likely fine and the
  problem is at the app layer. Check Uvicorn logs and middleware configuration.
- If you see bytes starting with 16 03 ... (hex) — this is a TLS ClientHello. The server is
  receiving TLS; either terminate TLS before the backend or run the backend with TLS certs.
- If the logger shows many non-printable or truncated bytes — MTU/MSS fragmentation is likely.

Persistence

- To persist iptables rules on Debian/Ubuntu: install iptables-persistent and run:

  netfilter-persistent save

- To persist MTU changes, add `MTU = 1280` in your WireGuard config or set MTU at boot.

If you want, I can guide you step-by-step through running these commands and interpreting output.
