#!/usr/bin/env bash
set -euo pipefail

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

SCRIPT_NAME="$(basename "$0")"

# ── Defaults ─────────────────────────────────────────────────
CONTAINER_NAME="amnezia-awg2"
CONFIG_DIR="/opt/amnezia/awg"
CONFIG_FILE="awg0.conf"
CLIENTS_TABLE="clientsTable"
AWG_INTERFACE="awg0"
SUBNET="10.8.1"
DNS="1.1.1.1"
KEEPALIVE=25

# ── Summary ──────────────────────────────────────────────────
print_summary() {
  cat >&2 <<EOF
=== awg-user-add ===
Add a new AmneziaWG 2.0 user to a remote Docker server.
Generates a working client config (without PresharedKey) and
applies it live without interrupting existing connections.

Usage:
  $SCRIPT_NAME <username> [<user>@]<host>[:<port>]

Examples:
  $SCRIPT_NAME Ivan root@1.2.3.4
  $SCRIPT_NAME Ivan 1.2.3.4
  $SCRIPT_NAME Ivan root@1.2.3.4:48452
EOF
}

die() {
  echo -e "${RED}Error:${NC} $*" >&2
  exit 1
}

# ── Params ───────────────────────────────────────────────────
CLIENT_NAME=""
SSH_DEST=""
SSH_USER="${SSH_USER:-root}"
SSH_HOST="${SSH_HOST:-}"
SSH_PORT=""
SSH_PASS=""

POSITIONAL=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --help) print_summary; exit 0 ;;
    -*)
      die "Unknown option: $1. Use --help for usage."
      ;;
    *)
      POSITIONAL+=("$1")
      shift
      ;;
  esac
done

set -- "${POSITIONAL[@]}"

if [ $# -ge 1 ]; then
  CLIENT_NAME="$1"
fi
if [ $# -ge 2 ]; then
  SSH_DEST="$2"
fi

# Parse SSH_DEST = [user@]host[:port]
if [ -n "$SSH_DEST" ]; then
  if [[ "$SSH_DEST" == *"@"* ]]; then
    SSH_USER="${SSH_DEST%%@*}"
    SSH_DEST="${SSH_DEST#*@}"
  fi
  if [[ "$SSH_DEST" == *":"* ]]; then
    SSH_PORT="${SSH_DEST##*:}"
    SSH_DEST="${SSH_DEST%:*}"
  fi
  SSH_HOST="$SSH_DEST"
fi

# ── Interactive prompt ──────────────────────────────────────
if [ -z "$SSH_HOST" ] || [ -z "$CLIENT_NAME" ]; then
  print_summary
fi

if [ -z "$CLIENT_NAME" ]; then
  read -r -p "Enter username: " CLIENT_NAME </dev/tty
  CLIENT_NAME="${CLIENT_NAME%% }"
  [ -z "$CLIENT_NAME" ] && die "Username is required"
fi

if [ -z "$SSH_HOST" ]; then
  read -r -p "Enter server [user@]host[:port]: " SSH_RAW </dev/tty
  SSH_RAW="${SSH_RAW%% }"
  [ -z "$SSH_RAW" ] && die "Server is required"

  if [[ "$SSH_RAW" == *"@"* ]]; then
    SSH_USER="${SSH_RAW%%@*}"
    SSH_RAW="${SSH_RAW#*@}"
  fi
  if [[ "$SSH_RAW" == *":"* ]]; then
    SSH_PORT="${SSH_RAW##*:}"
    SSH_RAW="${SSH_RAW%:*}"
  fi
  SSH_HOST="$SSH_RAW"
fi

  echo "SSH password:" >&2
  read -r -s SSH_PASS </dev/tty
  echo >&2

# ── Pre-flight ──────────────────────────────────────────────
echo "--- Pre-flight ---"

[ -z "$SSH_HOST" ] && die "Server hostname is required"
[ -z "$CLIENT_NAME" ] && die "Username is required"

NAME_REGEX='^[a-zA-Z0-9_]([a-zA-Z0-9_ -]{0,48}[a-zA-Z0-9_])?$'
if ! echo "$CLIENT_NAME" | grep -qE "$NAME_REGEX"; then
  die "Invalid username. Use letters, digits, spaces, hyphens, underscores."
fi

SSHPASS_BIN=""
for p in sshpass /tmp/sshpass_extract/usr/bin/sshpass; do
  command -v "$p" &>/dev/null && { SSHPASS_BIN="$p"; break; }
done

for cmd in ssh python3; do
  if command -v "$cmd" &>/dev/null; then
    echo -e "  $(printf '%-20s' "$cmd:") ${GREEN}found${NC}"
  else
    die "$(printf '%-20s' "$cmd:") ${RED}failed${NC} — required"
  fi
done

if [ -z "$SSHPASS_BIN" ]; then
  die "sshpass not found — install it or use SSH keys"
fi
echo -e "  $(printf '%-20s' "sshpass:") ${GREEN}found${NC} at $SSHPASS_BIN"

if [ -n "$SSH_PORT" ]; then
  SSH_BASE=("$(command -v "$SSHPASS_BIN")" -p "$SSH_PASS" ssh -o StrictHostKeyChecking=accept-new -o ConnectTimeout=10 -p "$SSH_PORT" "${SSH_USER}@${SSH_HOST}")
else
  SSH_BASE=("$(command -v "$SSHPASS_BIN")" -p "$SSH_PASS" ssh -o StrictHostKeyChecking=accept-new -o ConnectTimeout=10 "${SSH_USER}@${SSH_HOST}")
fi

# ── Execute remote script ───────────────────────────────────
echo ""
echo "--- Adding user: ${CYAN}${CLIENT_NAME}${NC} on ${CYAN}${SSH_HOST}${NC} ---"
echo ""

"${SSH_BASE[@]}" bash -s "$CLIENT_NAME" "$SSH_HOST" << 'RS'
set -euo pipefail

CONTAINER_NAME="amnezia-awg2"
CONFIG_DIR="/opt/amnezia/awg"
CONFIG_FILE="awg0.conf"
CLIENTS_TABLE="clientsTable"
AWG_INTERFACE="awg0"
SUBNET="10.8.1"
DNS="1.1.1.1"
KEEPALIVE=25
CLIENT_NAME="$1"
SERVER_HOST="$2"

echo "  Generating keys..."
CLIENT_PRIV_KEY=$(docker exec "$CONTAINER_NAME" awg genkey)
CLIENT_PUB_KEY=$(echo "$CLIENT_PRIV_KEY" | docker exec -i "$CONTAINER_NAME" awg pubkey)

echo "  Getting server config..."
SERVER_PUB_KEY=$(docker exec "$CONTAINER_NAME" sh -c "cat ${CONFIG_DIR}/wireguard_server_public_key.key" 2>/dev/null || \
                 docker exec "$CONTAINER_NAME" awg show "$AWG_INTERFACE" public-key)

SERVER_LISTEN_PORT=$(docker exec "$CONTAINER_NAME" sh -c "grep ^ListenPort ${CONFIG_DIR}/${CONFIG_FILE} | awk '{print \$3}'")
SERVER_EXT_PORT=$(docker port "$CONTAINER_NAME" 2>/dev/null | grep -oE '0\.0\.0\.0:[0-9]+' | head -1 | cut -d: -f2 || echo "$SERVER_LISTEN_PORT")
echo "  Reading AWG parameters..."
AWG_PARAMS=$(docker exec "$CONTAINER_NAME" sh -c "grep -E -i '^(Jc|Jmin|Jmax|S1|S2|S3|S4|H1|H2|H3|H4|i1|i2|i3|i4|i5)[[:space:]]*=' ${CONFIG_DIR}/${CONFIG_FILE}" 2>/dev/null || \
  docker exec "$CONTAINER_NAME" sh -c "grep -E -i '^[[:space:]]*(Jc|Jmin|Jmax|S1|S2|S3|S4|H1|H2|H3|H4|i1|i2|i3|i4|i5)[[:space:]]*=' ${CONFIG_DIR}/${CONFIG_FILE}")

echo "  Finding free IP..."
USED_IPS=$(docker exec "$CONTAINER_NAME" sh -c "grep -oE '${SUBNET//\./\\.}\.[0-9]+' ${CONFIG_DIR}/${CONFIG_FILE} | grep -v '\.0$' || true")
NEXT_OCTET=2
for octet in $(echo "$USED_IPS" | grep -oE '[0-9]+$' | sort -n); do
  [ "$octet" -ge "$NEXT_OCTET" ] && NEXT_OCTET=$((octet + 1))
done
CLIENT_IP="${SUBNET}.${NEXT_OCTET}/32"

EXISTING=$(docker exec "$CONTAINER_NAME" sh -c "grep -c ${CLIENT_PUB_KEY} ${CONFIG_DIR}/${CONFIG_FILE}" 2>/dev/null || true)
if [ "$EXISTING" -gt 0 ]; then
  echo "  WARNING: peer already exists, but continuing..."
fi

echo "  Writing to config file..."
docker exec "$CONTAINER_NAME" sh -c "printf '\n[Peer]\nPublicKey = %s\nAllowedIPs = %s\n' '${CLIENT_PUB_KEY}' '${CLIENT_IP}' >> ${CONFIG_DIR}/${CONFIG_FILE}"

echo "  Adding to running interface..."
docker exec "$CONTAINER_NAME" awg set "$AWG_INTERFACE" peer "$CLIENT_PUB_KEY" allowed-ips "$CLIENT_IP"

echo "  Updating clients table..."
CLIENTS_JSON=$(docker exec "$CONTAINER_NAME" sh -c "cat ${CONFIG_DIR}/${CLIENTS_TABLE}" 2>/dev/null || echo "[]")
UPDATED=$(echo "$CLIENTS_JSON" | python3 -c "
import json, sys
data = json.load(sys.stdin)
data = [d for d in data if d.get('clientId') != '${CLIENT_PUB_KEY}']
data.append({
    'clientId': '${CLIENT_PUB_KEY}',
    'userData': {
        'allowedIps': '${CLIENT_IP}',
        'clientName': '${CLIENT_NAME}',
        'creationDate': '$(date)'
    }
})
print(json.dumps(data, indent=4))
" 2>/dev/null || echo "")
[ -n "$UPDATED" ] && echo "$UPDATED" | docker exec -i "$CONTAINER_NAME" sh -c "cat > ${CONFIG_DIR}/${CLIENTS_TABLE}"

echo ""
echo "=== CLIENT CONFIG ==="
echo ""
echo "[Interface]"
echo "PrivateKey = ${CLIENT_PRIV_KEY}"
echo "Address = ${CLIENT_IP}"
echo "DNS = ${DNS}"
echo "${AWG_PARAMS}"
echo ""
echo "[Peer]"
echo "PublicKey = ${SERVER_PUB_KEY}"
echo "Endpoint = ${SERVER_HOST}:${SERVER_EXT_PORT}"
echo "AllowedIPs = 0.0.0.0/0, ::/0"
echo "PersistentKeepalive = ${KEEPALIVE}"
echo ""
echo "=== END CONFIG ==="
RS
