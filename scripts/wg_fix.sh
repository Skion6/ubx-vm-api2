#!/usr/bin/env bash
set -euo pipefail
# scripts/wg_fix.sh
# Help apply common WireGuard tunnel fixes for MTU and TCPMSS on the VPS.
# Usage: sudo ./scripts/wg_fix.sh [wg-interface] [mtu]

WG_IF="${1:-wg0}"
MTU="${2:-1280}"

echo "[wg_fix] Setting MTU=${MTU} on interface ${WG_IF}"
if ip link show "$WG_IF" >/dev/null 2>&1; then
    ip link set dev "$WG_IF" mtu "$MTU"
    echo "[wg_fix] MTU set"
else
    echo "[wg_fix] Interface $WG_IF not found; skipping MTU set" >&2
fi

echo "[wg_fix] Ensuring TCPMSS clamping on FORWARD chain"
# Add rule only if it doesn't exist yet
if ! iptables -t mangle -C FORWARD -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --clamp-mss-to-pmtu 2>/dev/null; then
    iptables -t mangle -A FORWARD -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --clamp-mss-to-pmtu
    echo "[wg_fix] iptables rule added"
else
    echo "[wg_fix] iptables rule already present"
fi

echo "[wg_fix] Current mangle FORWARD rules:"
iptables -t mangle -vnL FORWARD || true

cat <<'EOF'
Done.

Notes / persistence:
- To persist iptables rules on Debian/Ubuntu: install iptables-persistent and run `netfilter-persistent save`.
- Alternatively add the iptables command to a startup script or a systemd unit.
- WireGuard MTU is best set in the WireGuard config (`/etc/wireguard/wg0.conf`) under the [Interface] section
  or via `ip link set dev <iface> mtu 1280` at boot.
EOF
