#!/usr/bin/env bash
set -euo pipefail

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

SCRIPT_NAME="$(basename "$0")"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
NET_TOOL="$PROJECT_ROOT/tools/linux-net-tool/net-tool.sh"
CONFIG_FILE="/etc/amnezia/amneziawg/wg0.conf"
AMNEZIA_PRIO_PATTERN='not from all fwmark.*lookup 51820'

# ── Summary ──────────────────────────────────────────────────
print_summary() {
  cat >&2 <<EOF
=== amnezia-symmetric-enable ===
Configure symmetric routing for AmneziaWG in $CONFIG_FILE

Modes:
  enable   — add/replace symmetric routing block for the given interface
  disable  — remove symmetric routing block for the given interface

Usage:
  $SCRIPT_NAME [enable|disable] [<interface>] [--no-restart]

Examples:
  $SCRIPT_NAME                                   interactive
  $SCRIPT_NAME enable                            use active interface
  $SCRIPT_NAME disable eno1                      remove block for eno1
  $SCRIPT_NAME enable eno1 --no-restart          add block, skip restart

EOF
}

# ── Helpers ──────────────────────────────────────────────────
die() {
  echo -e "${RED}Error:${NC} $*" >&2
  exit 1
}

amnezia_service() {
  for svc in awg-quick@wg0.service amneziawg@wg0.service amneziawg-quick@wg0.service wg-quick@wg0.service; do
    if systemctl is-active --quiet "$svc" 2>/dev/null; then
      echo "$svc"
      return 0
    fi
  done

  for svc in awg-quick@wg0.service amneziawg@wg0.service wg-quick@wg0.service; do
    if systemctl is-enabled --quiet "$svc" 2>/dev/null; then
      echo "$svc"
      return 0
    fi
  done

  return 1
}

amnezia_running() {
  amnezia_service >/dev/null 2>&1 && return 0
  ip link show awg0 2>/dev/null | grep -q 'UP' && return 0
  ip link show wg0 2>/dev/null | grep -q 'UP' && return 0
  return 1
}

block_start_marker() {
  echo "### AUTOMATO/CONFIGURE/AMNEZIA-CONFIGURE-SYMMETRIC-${1} START ###"
}

block_end_marker() {
  echo "### AUTOMATO/CONFIGURE/AMNEZIA-CONFIGURE-SYMMETRIC-${1} END ###"
}

generate_block() {
  local iface="$1" mark="$2" table="$3" mask="$4" gateway="$5" priority="$6"
  local start end
  start=$(block_start_marker "$iface")
  end=$(block_end_marker "$iface")

  cat <<BLOCK

$start
#
# Симметричный роутинг для amneziawg
#
# Исходящие пакеты ответов на входящие соединения с ethernet (${iface}) - отправляем через этот же интерфейс.
# Без этого исходящие пакеты завернутся в amnezia и клиенты их никогда не получат.
#
# Есть более простой вариант - ip route add ${mask} dev ${iface} metric 50
# но он не обрабатывает ситуацию когда входящее соединение идет через интернет и локальную сеть,
# напрмер обращения к роутеру на котором проброшены порты до сервера.

# Применяем при поднятии amneniawg
# Сначала удаляем старые правила на случай если завершение прошло неудачно
PostUp = ip rule del fwmark ${mark} table ${table} priority ${priority} 2>/dev/null || true
PostUp = iptables -t mangle -D PREROUTING -i ${iface} -m conntrack --ctstate NEW -j CONNMARK --set-mark ${mark} 2>/dev/null || true
PostUp = iptables -t mangle -D OUTPUT -m conntrack --ctstate ESTABLISHED,RELATED -j CONNMARK --restore-mark 2>/dev/null || true
PostUp = ip route flush table ${table} 2>/dev/null || true
# Затем добавляем актуальные
PostUp = iptables -t mangle -A PREROUTING -i ${iface} -m conntrack --ctstate NEW -j CONNMARK --set-mark ${mark}
PostUp = iptables -t mangle -A OUTPUT -m conntrack --ctstate ESTABLISHED,RELATED -j CONNMARK --restore-mark
PostUp = ip rule add fwmark ${mark} table ${table} priority ${priority}
PostUp = ip route add ${mask} dev ${iface} table ${table}
PostUp = ip route add default via ${gateway} dev ${iface} table ${table}

# При отключении amneziawg - удаляем все что создали
PreDown = ip rule del fwmark ${mark} table ${table} priority ${priority} 2>/dev/null || true
PreDown = iptables -t mangle -D PREROUTING -i ${iface} -m conntrack --ctstate NEW -j CONNMARK --set-mark ${mark} 2>/dev/null || true
PreDown = iptables -t mangle -D OUTPUT -m conntrack --ctstate ESTABLISHED,RELATED -j CONNMARK --restore-mark 2>/dev/null || true
PreDown = ip route flush table ${table} 2>/dev/null || true
#
$end

BLOCK
}

remove_block() {
  local iface="$1"
  local start end
  start=$(block_start_marker "$iface")
  end=$(block_end_marker "$iface")

  if [ ! -f "$CONFIG_FILE" ]; then
    echo -e "  ${YELLOW}skip${NC} $CONFIG_FILE does not exist"
    return 0
  fi

  if grep -qF "$start" "$CONFIG_FILE" 2>/dev/null; then
    echo "  Removing existing block for interface $iface..."
    sed -i "/^$(printf '%s' "$start" | sed 's/[\/&]/\\&/g')$/,/^$(printf '%s' "$end" | sed 's/[\/&]/\\&/g')$/d" "$CONFIG_FILE"
    echo -e "  ${RED}-${NC} $CONFIG_FILE — removed block for $iface"
  else
    echo -e "  ${YELLOW}skip${NC} no block found for interface $iface"
  fi
}

insert_block() {
  local iface="$1" mark="$2" table="$3" mask="$4" gateway="$5" priority="$6"
  local start end block_file
  start=$(block_start_marker "$iface")
  end=$(block_end_marker "$iface")

  # Write generated block to a temp file
  block_file=$(mktemp)
  generate_block "$iface" "$mark" "$table" "$mask" "$gateway" "$priority" > "$block_file"

  # Create file with [Interface] if it doesn't exist
  if [ ! -f "$CONFIG_FILE" ]; then
    mkdir -p "$(dirname "$CONFIG_FILE")"
    printf '[Interface]\n' > "$CONFIG_FILE"
  fi

  if ! grep -q '^\[Interface\]' "$CONFIG_FILE" 2>/dev/null; then
    sed -i '1s/^/[Interface]\n/' "$CONFIG_FILE"
  fi

  # Read all lines into array
  mapfile -t lines < "$CONFIG_FILE"

  # Find insertion point: line index of first [Peer], or end of array
  insert_at=${#lines[@]}
  for i in "${!lines[@]}"; do
    if [[ "${lines[$i]}" == "[Peer]"* ]]; then
      insert_at=$i
      break
    fi
  done

  # Strip trailing blank lines before insertion point
  while [ "$insert_at" -gt 0 ] && [ -z "${lines[$((insert_at - 1))]}" ]; do
    insert_at=$((insert_at - 1))
  done

  # Rebuild file with block inserted
  {
    # Lines before insertion point
    for ((i = 0; i < insert_at; i++)); do
      printf '%s\n' "${lines[$i]}"
    done

    # Block (includes leading blank line, content, trailing blank line)
    cat "$block_file"

    # Lines from insertion point (first [Peer] or end)
    for ((i = insert_at; i < ${#lines[@]}; i++)); do
      printf '%s\n' "${lines[$i]}"
    done
  } > "$CONFIG_FILE"

  rm -f "$block_file"
  echo -e "  ${GREEN}+${NC} $CONFIG_FILE — added symmetric routing block for $iface"
}

detect_active_iface() {
  local iface
  iface=$("$NET_TOOL" active 2>/dev/null | tail -1)
  if [ -z "$iface" ]; then
    die "No active interface found and none specified"
  fi
  echo "$iface"
}

detect_amnezia_priority() {
  local prio
  prio=$("$NET_TOOL" priority down "$AMNEZIA_PRIO_PATTERN" 2>/dev/null | tail -1)
  if [ -z "$prio" ] || ! [[ "$prio" =~ ^[0-9]+$ ]]; then
    echo "32760"
  else
    echo "$prio"
  fi
}

# ── Interactive prompt ──────────────────────────────────────
interactive_prompt() {
  echo "Select mode:" >&2
  echo "  1) enable" >&2
  echo "  2) disable" >&2
  read -r -p "Enter number [1-2]: " choice </dev/tty
  echo >&2

  case "$choice" in
    1) MODE="enable" ;;
    2) MODE="disable" ;;
    *)
      echo -e "${RED}Error:${NC} invalid choice '$choice'" >&2
      exit 1
      ;;
  esac

  mapfile -t ifaces < <("$NET_TOOL" ifaces 2>/dev/null)

  echo "Available interfaces:" >&2
  for i in "${!ifaces[@]}"; do
    printf "  %d) %s\n" $((i + 1)) "${ifaces[$i]}" >&2
  done
  read -r -p "Select interface [1-${#ifaces[@]}]: " choice </dev/tty
  echo >&2

  if ! [[ "$choice" =~ ^[0-9]+$ ]] || [ "$choice" -lt 1 ] || [ "$choice" -gt "${#ifaces[@]}" ]; then
    echo -e "${RED}Error:${NC} invalid choice '$choice'" >&2
    exit 1
  fi

  IFACE="${ifaces[$((choice - 1))]}"
}

# ── Pre-flight checks ───────────────────────────────────────
preflight() {
  echo "--- Pre-flight ---"

  if [ "$EUID" -ne 0 ]; then
    echo -e "  $(printf '%-28s' "root:") ${RED}failed${NC} — run with sudo"
    return 1
  fi
  echo -e "  $(printf '%-28s' "root:") ${GREEN}passed${NC}"

  if ! command -v ip &>/dev/null; then
    echo -e "  $(printf '%-28s' "ip (iproute2):") ${RED}failed${NC}"
    return 1
  fi
  echo -e "  $(printf '%-28s' "ip (iproute2):") ${GREEN}passed${NC}"

  if ! command -v iptables &>/dev/null; then
    echo -e "  $(printf '%-28s' "iptables:") ${RED}failed${NC}"
    return 1
  fi
  echo -e "  $(printf '%-28s' "iptables:") ${GREEN}passed${NC}"

  if ! command -v sed &>/dev/null; then
    echo -e "  $(printf '%-28s' "sed:") ${RED}failed${NC}"
    return 1
  fi
  echo -e "  $(printf '%-28s' "sed:") ${GREEN}passed${NC}"

  if ! command -v systemctl &>/dev/null; then
    echo -e "  $(printf '%-28s' "systemctl:") ${YELLOW}warn${NC} — not found, skip service restart"
  else
    echo -e "  $(printf '%-28s' "systemctl:") ${GREEN}passed${NC}"
  fi

  return 0
}

check_net_tool() {
  if [ ! -x "$NET_TOOL" ]; then
    echo -e "  $(printf '%-28s' "net-tool.sh:") ${RED}failed${NC} — not found at $NET_TOOL"
    return 1
  fi
  echo -e "  $(printf '%-28s' "net-tool.sh:") ${GREEN}passed${NC}"
  return 0
}

# ── Main ─────────────────────────────────────────────────────
print_summary

# Parse arguments
NO_RESTART=false
MODE=""
IFACE=""

for arg in "$@"; do
  case "$arg" in
    --no-restart) NO_RESTART=true ;;
    enable|disable) MODE="$arg" ;;
    *)
      if [[ "$arg" != --* ]]; then
        IFACE="$arg"
      fi
      ;;
  esac
done

# Pre-flight checks — run before any prompts
if ! preflight; then
  die "Pre-flight checks failed"
fi

# Interactive prompt if no mode given
if [ "$MODE" != "enable" ] && [ "$MODE" != "disable" ]; then
  interactive_prompt
fi

# Interface: from arg or detect
if [ -z "$IFACE" ]; then
  echo "No interface specified, detecting active interface..."
  IFACE=$(detect_active_iface)
  echo "Active interface: $IFACE"
fi

# Validate interface
if ! ip link show "$IFACE" &>/dev/null; then
  die "Interface '$IFACE' does not exist"
fi

echo ""

# ── Disable mode ────────────────────────────────────────────
if [ "$MODE" = "disable" ]; then
  WAS_RUNNING=false
  amnezia_running && WAS_RUNNING=true

  remove_block "$IFACE"

  if $WAS_RUNNING && ! $NO_RESTART; then
    echo "Restarting AmneziaWG..."
    SVC=$(amnezia_service 2>/dev/null || true)
    if [ -n "$SVC" ]; then
      systemctl restart "$SVC"
    else
      systemctl restart amneziawg@wg0 2>/dev/null || \
      systemctl restart wg-quick@wg0 2>/dev/null || true
    fi
  fi

  echo ""
  echo "Done. Block for $IFACE removed."
  exit 0
fi

# ── Enable mode ─────────────────────────────────────────────
if ! check_net_tool; then
  die "Pre-flight checks failed"
fi

# Fetch network parameters from net-tool.sh
echo "Fetching network parameters for $IFACE..."

NET_MARK=$("$NET_TOOL" mark 2>/dev/null | tail -1) || die "Failed to get free mark"
NET_TABLE=$("$NET_TOOL" table 2>/dev/null | tail -1) || die "Failed to get free table"
NET_MASK=$("$NET_TOOL" mask "$IFACE" 2>/dev/null | tail -1) || die "Failed to get subnet for $IFACE"
NET_GATEWAY=$("$NET_TOOL" gateway "$IFACE" 2>/dev/null | tail -1) || die "Failed to get gateway for $IFACE"

echo "  Interface: $IFACE"
echo "  Mark:      $NET_MARK"
echo "  Table:     $NET_TABLE"
echo "  Subnet:    $NET_MASK"
echo "  Gateway:   $NET_GATEWAY"

NET_PRIORITY=$(detect_amnezia_priority)
echo "  Priority:  $NET_PRIORITY (below AmneziaWG)"
echo ""

WAS_RUNNING=false
amnezia_running && WAS_RUNNING=true

remove_block "$IFACE"
insert_block "$IFACE" "$NET_MARK" "$NET_TABLE" "$NET_MASK" "$NET_GATEWAY" "$NET_PRIORITY"

if $WAS_RUNNING && ! $NO_RESTART; then
  echo "Restarting AmneziaWG..."
  SVC=$(amnezia_service 2>/dev/null || true)
  if [ -n "$SVC" ]; then
    systemctl restart "$SVC"
  else
    systemctl restart amneziawg@wg0 2>/dev/null || \
    systemctl restart wg-quick@wg0 2>/dev/null || true
  fi
fi

echo ""
echo "Done. Symmetric routing configured for $IFACE in $CONFIG_FILE"
