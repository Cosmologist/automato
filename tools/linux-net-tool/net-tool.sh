#!/usr/bin/env bash
set -euo pipefail

SCRIPT_NAME="$(basename "$0")"
ALLOW_NO_RESULT=false
ALL_MODE=false

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# ── Summary ──────────────────────────────────────────────────
print_summary() {
  cat >&2 <<EOF
--- Linux Net Tool ---
Displays network information about the current machine.

Usage:
  $SCRIPT_NAME [--allow-no-result] [--all] active   — Print primary interface (or all with --all)
  $SCRIPT_NAME [--allow-no-result] [--all] ifaces   — List interfaces (physical only, or all with --all)
  $SCRIPT_NAME [--allow-no-result] priority <up|down> <pattern> — Find ip rule priority by pattern
  $SCRIPT_NAME [--allow-no-result] mark                        — Print a free iptables fwmark value (hex)
  $SCRIPT_NAME [--allow-no-result] table                       — Print a free routing table number
  $SCRIPT_NAME [--allow-no-result] mask      [<interface>]     — Print subnet (CIDR) for an interface
  $SCRIPT_NAME [--allow-no-result] gateway   [<interface>]     — Print gateway for an interface
  $SCRIPT_NAME [--allow-no-result] env       [<interface>]     — Print export statements for all modes

Without --allow-no-result: exits with code 1 when nothing found.
With    --allow-no-result: prints empty string and exits with code 0.

Examples:
  IFACE=\$($SCRIPT_NAME active)
  $SCRIPT_NAME ifaces                     # => eno1, enp0s31f6, ...
  $SCRIPT_NAME ifaces --all               # => lo, eno1, wg0, ...
  $SCRIPT_NAME priority down 'not from all fwmark.*lookup 51820'  # => 32760
  $SCRIPT_NAME mark                       # => 0x100
  $SCRIPT_NAME table                      # => 1
  $SCRIPT_NAME mask                       # uses active interface
  $SCRIPT_NAME gateway eno1               # => 192.168.1.1
  eval "\$($SCRIPT_NAME env)"

EOF
}

# ── Pre-flight checks ────────────────────────────────────────
preflight() {
  if ! command -v ip &>/dev/null; then
    echo "Error: 'ip' command not found (package iproute2 required)." >&2
    return 1
  fi
}

# ── Helpers ──────────────────────────────────────────────────
no_result() {
  local msg="$1"
  echo "$msg" >&2
  if $ALLOW_NO_RESULT; then
    echo ""
    exit 0
  else
    exit 1
  fi
}

is_physical() {
  test -L "/sys/class/net/$1/device"
}

all_iface_list() {
  ip -br link show 2>/dev/null | awk '{print $1}'
}

physical_iface_list() {
  local iface
  for iface in /sys/class/net/*; do
    iface=$(basename "$iface")
    if is_physical "$iface"; then
      echo "$iface"
    fi
  done
}

pick_primary() {
  local default_iface
  default_iface=$(ip route show default 2>/dev/null | awk '{print $5; exit}')

  local candidate

  # Prefer the interface with the default route
  if [ -n "$default_iface" ]; then
    while IFS= read -r candidate; do
      if [ "$candidate" = "$default_iface" ]; then
        echo "$candidate"
        return 0
      fi
    done
  fi

  # Fallback: first candidate with an IPv4 address
  while IFS= read -r candidate; do
    if ip -o -4 addr show dev "$candidate" 2>/dev/null | grep -q .; then
      echo "$candidate"
      return 0
    fi
  done

  # Last resort: first candidate
  while IFS= read -r candidate; do
    echo "$candidate"
    return 0
  done
}

# ── Mode: active ────────────────────────────────────────────
cmd_active() {
  if $ALL_MODE; then
    echo "Looking for primary interface (physical + virtual)..." >&2
    local first
    first=$(all_iface_list | pick_primary)
  else
    echo "Looking for primary physical interface..." >&2
    local first
    first=$(physical_iface_list | pick_primary)
  fi
  if [ -z "$first" ]; then
    no_result "No primary interface found"
  fi
  echo "Found: $first" >&2
  echo "$first"
}

# ── Mode: ifaces ─────────────────────────────────────────────
cmd_ifaces() {
  if $ALL_MODE; then
    echo "Listing all interfaces (physical + virtual)..." >&2
    all_iface_list
  else
    echo "Listing physical interfaces..." >&2
    physical_iface_list
  fi
}

# ── Mode: priority ────────────────────────────────────────────
cmd_priority() {
  local direction="$1"
  local pattern="$2"

  if [ -z "$direction" ] || [ -z "$pattern" ]; then
    echo "Usage: $SCRIPT_NAME priority <up|down> <grep-pattern>" >&2
    echo "  up   — print priority of ip rule matching pattern" >&2
    echo "  down — print priority one below the matched rule" >&2
    echo "" >&2
    echo "Examples:" >&2
    echo "  $SCRIPT_NAME priority down 'not from all fwmark.*lookup 51820'" >&2
    echo "  => 32760 (one below AmneziaWG rule at 32761)" >&2
    return 1
  fi

  local matched_prio
  matched_prio=$(ip rule show 2>/dev/null | grep -P "$pattern" | head -1 | grep -oP '^\d+')

  if [ -z "$matched_prio" ]; then
    no_result "No ip rule matching pattern: $pattern"
  fi

  case "$direction" in
    up)
      echo "Matched priority: $matched_prio" >&2
      echo "$matched_prio"
      ;;
    down)
      local new_prio=$((matched_prio - 1))
      if [ "$new_prio" -lt 0 ]; then
        no_result "Cannot go below priority 0 (matched $matched_prio)"
      fi
      echo "Priority below $matched_prio: $new_prio" >&2
      echo "$new_prio"
      ;;
    *)
      echo "Invalid direction: $direction (use 'up' or 'down')" >&2
      return 1
      ;;
  esac
}

# ── Mode: mark ───────────────────────────────────────────────
cmd_mark() {
  echo "Scanning for free iptables fwmark..." >&2

  if ! command -v iptables-save &>/dev/null; then
    echo "iptables-save not available — checking ip rules only" >&2
  fi

  local -A used
  local line hex norm

  # Collect used marks from iptables rules (all tables)
  if command -v iptables-save &>/dev/null; then
    while IFS= read -r line; do
      [[ -z "$line" ]] && continue
      # Normalize: store all marks as hex keys
      if [[ "$line" =~ ^0x ]]; then
        used[$line]=1
      else
        norm=$(printf "0x%x" "$line")
        used[$norm]=1
      fi
    done < <(iptables-save 2>/dev/null | grep -oP '\-\-set-mark (0x[0-9a-fA-F]+|[0-9]+)' | awk '{print $NF}')
  fi

  # Collect used marks from ip rules
  while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    used[$line]=1
  done < <(ip rule show 2>/dev/null | grep -oP 'fwmark \K[0-9a-fx]+')

  # Find first free mark starting at 0x100
  for ((i = 256; i <= 65535; i++)); do
    hex=$(printf "0x%x" "$i")
    if [[ -z "${used[$hex]:-}" ]]; then
      echo "Free mark: $hex" >&2
      echo "$hex"
      return 0
    fi
  done

  no_result "No free fwmark found in range 0x100–0xffff"
}

# ── Mode: table ──────────────────────────────────────────────
cmd_table() {
  echo "Scanning for free routing table number..." >&2

  local -A used
  local line num

  # Read iproute2 table definition files
  for f in /etc/iproute2/rt_tables /run/iproute2/rt_tables; do
    if [ -f "$f" ]; then
      while IFS=' ' read -r num _; do
        [[ "$num" =~ ^[0-9]+$ ]] && used[$num]=1
      done < "$f"
    fi
  done

  # Collect table numbers from routing rules and routes
  while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    used[$line]=1
  done < <(ip route show table all 2>/dev/null | grep -oP 'table \K[0-9]+' | sort -u) || true

  while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    used[$line]=1
  done < <(ip rule show 2>/dev/null | grep -oP 'lookup \K[0-9]+') || true

  # Reserved tables: 0 (unspec), 253 (default), 254 (main), 255 (local)
  used[0]=1
  used[253]=1
  used[254]=1
  used[255]=1

  # Find gaps in used set: scan 1–252, then find next gap from sorted used values
  local max_used=0
  local sorted
  sorted=$(printf "%s\n" "${!used[@]}" | sort -n)

  for i in 1 2 3 4 5 6 7 8 9 10; do
    if [[ -z "${used[$i]:-}" ]]; then
      echo "Free table: $i" >&2
      echo "$i"
      return 0
    fi
  done

  # Scan higher ranges by finding gaps between consecutive used values
  local prev=0
  while IFS= read -r num; do
    if [ "$num" -gt "$prev" ] && [ "$prev" -gt 0 ] && [ "$((num - prev))" -gt 1 ]; then
      local candidate=$((prev + 1))
      echo "Free table: $candidate" >&2
      echo "$candidate"
      return 0
    fi
    prev=$num
  done <<< "$sorted"

  # No gap found; return one past the max
  local candidate=$((prev + 1))
  if [ "$candidate" -lt 4294967295 ]; then
    echo "Free table: $candidate" >&2
    echo "$candidate"
    return 0
  fi

  no_result "No free table number found"
}

validate_iface() {
  local iface="$1"
  if ! ip link show "$iface" &>/dev/null; then
    echo "Interface '$iface' does not exist" >&2
    exit 1
  fi
}

prompt_iface() {
  local ifaces
  mapfile -t ifaces < <(ip -br link show | awk '{print $1}')
  echo "Available interfaces:" >&2
  for i in "${!ifaces[@]}"; do
    printf "  %d) %s\n" $((i + 1)) "${ifaces[$i]}" >&2
  done
  read -r -p "Select interface [1-${#ifaces[@]}]: " choice </dev/tty
  echo >&2
  if ! [[ "$choice" =~ ^[0-9]+$ ]] || [ "$choice" -lt 1 ] || [ "$choice" -gt "${#ifaces[@]}" ]; then
    echo "Invalid choice: $choice" >&2
    exit 1
  fi
  IFACE="${ifaces[$((choice - 1))]}"
}

# ── Mode: mask ───────────────────────────────────────────────
cmd_mask() {
  local iface="${1:-}"
  if [ -z "$iface" ]; then
    iface=$(physical_iface_list | pick_primary)
    if [ -z "$iface" ]; then
      no_result "No active interface found"
    fi
    echo "Using active interface: $iface" >&2
  fi
  validate_iface "$iface"
  echo "Getting subnet for $iface..." >&2
  local network
  network=$(ip route show dev "$iface" 2>/dev/null | awk '/scope link/{print $1; exit}')
  if [ -z "$network" ]; then
    no_result "No subnet found for $iface"
  fi
  echo "Subnet: $network" >&2
  echo "$network"
}

# ── Mode: gateway ────────────────────────────────────────────
cmd_gateway() {
  local iface="${1:-}"
  if [ -z "$iface" ]; then
    iface=$(physical_iface_list | pick_primary)
    if [ -z "$iface" ]; then
      no_result "No active interface found"
    fi
    echo "Using active interface: $iface" >&2
  fi
  validate_iface "$iface"
  echo "Getting gateway for $iface..." >&2
  local gw
  gw=$(ip route show default dev "$iface" 2>/dev/null | awk '{print $3}')
  if [ -z "$gw" ]; then
    no_result "No default gateway found on $iface"
  fi
  echo "Gateway: $gw" >&2
  echo "$gw"
}

# ── Mode: env ────────────────────────────────────────────────
cmd_env() {
  local iface="${1:-}"
  if [ -z "$iface" ]; then
    iface=$(physical_iface_list | pick_primary)
    if [ -z "$iface" ]; then
      no_result "No active interface found"
    fi
    echo "Using active interface: $iface" >&2
  fi
  validate_iface "$iface"

  echo "Collecting network info for $iface..." >&2

  local val

  val=$(ALLOW_NO_RESULT=true cmd_active 2>/dev/null || true)
  [ -n "$val" ] && echo "export NETWORK_ACTIVE='$val'"

  val=$(ALLOW_NO_RESULT=true cmd_mark 2>/dev/null || true)
  [ -n "$val" ] && echo "export NETWORK_MARK='$val'"

  val=$(ALLOW_NO_RESULT=true cmd_table 2>/dev/null || true)
  [ -n "$val" ] && echo "export NETWORK_TABLE='$val'"

  val=$(ALLOW_NO_RESULT=true cmd_mask "$iface" 2>/dev/null || true)
  [ -n "$val" ] && echo "export NETWORK_MASK='$val'"

  val=$(ALLOW_NO_RESULT=true cmd_gateway "$iface" 2>/dev/null || true)
  [ -n "$val" ] && echo "export NETWORK_GATEWAY='$val'"
}

# ── Interactive prompt ──────────────────────────────────────
interactive_prompt() {
  echo "Select mode:" >&2
  echo "  1) active    — Show active physical interface(s)" >&2
  echo "  2) mark      — Show free iptables fwmark" >&2
  echo "  3) table     — Show free routing table number" >&2
  echo "  4) mask      — Show subnet for an interface" >&2
  echo "  5) gateway   — Show gateway for an interface" >&2
  echo "  6) env       — Export all values as NETWORK_* variables" >&2
  read -r -p "Enter number [1-6]: " choice </dev/tty
  echo >&2

  case "$choice" in
    1) MODE="active" ;;
    2) MODE="mark" ;;
    3) MODE="table" ;;
    4) MODE="mask" ;;
    5) MODE="gateway" ;;
    6) MODE="env" ;;
    *)
      echo "Invalid choice: $choice" >&2
      exit 1
      ;;
  esac
}

# ── Main ─────────────────────────────────────────────────────
print_summary

# Parse flags
ARGS=()
for arg in "$@"; do
  case "$arg" in
    --allow-no-result) ALLOW_NO_RESULT=true ;;
    --all) ALL_MODE=true ;;
    *) ARGS+=("$arg") ;;
  esac
done

MODE="${ARGS[0]:-}"
if [ -z "$MODE" ]; then
  interactive_prompt
fi

if ! preflight; then
  exit 1
fi

case "$MODE" in
  active | a)
    cmd_active
    ;;
  ifaces | i)
    cmd_ifaces
    ;;
  priority | p)
    cmd_priority "${ARGS[1]:-}" "${ARGS[2]:-}"
    ;;
  mark | m)
    cmd_mark
    ;;
  table | t)
    cmd_table
    ;;
  mask)
    cmd_mask "${ARGS[1]:-}"
    ;;
  gateway | gw)
    cmd_gateway "${ARGS[1]:-}"
    ;;
  env)
    cmd_env "${ARGS[1]:-}"
    ;;
  *)
    echo "Unknown mode: $MODE" >&2
    echo "  Valid modes: active, ifaces, priority, mark, table, mask, gateway, env" >&2
    exit 1
    ;;
esac
