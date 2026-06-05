#!/bin/bash
set -euo pipefail

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# ---------------------------------------------------------------------------
# Summary — printed on every invocation
# ---------------------------------------------------------------------------
echo "=== debian-apt-unstable-allow ==="
echo "Adds Debian unstable/testing repos to APT with pinning (priority 50)."
echo ""
echo "Usage:"
echo "  sudo ./apt-unstable-allow.sh --check              pre-flight checks only"
echo "  sudo ./apt-unstable-allow.sh                      interactive mode"
echo "  sudo ./apt-unstable-allow.sh unstable [testing]   specify suites"
echo ""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
SUITE_OK=0
SUITE_ALREADY=100

suite_configured() {
    local s="$1"
    if grep -rqs "^deb\s.*${s}"      /etc/apt/sources.list /etc/apt/sources.list.d/ 2>/dev/null ||
       grep -rqs "^Suites:\s*.*${s}" /etc/apt/sources.list /etc/apt/sources.list.d/ 2>/dev/null; then
        return "$SUITE_ALREADY"
    fi
    return "$SUITE_OK"
}

# ---------------------------------------------------------------------------
# Pre-flight checks
# ---------------------------------------------------------------------------
preflight() {
    local all_passed=0
    local has_sudo=0

    echo "--- Pre-flight ---"

    if [ "$EUID" -eq 0 ]; then
        echo -e "  $(printf '%-32s' "• root:") ${GREEN}passed${NC}"
        has_sudo=1
    elif command -v sudo &>/dev/null && sudo -n true 2>/dev/null; then
        echo -e "  $(printf '%-32s' "• sudo:") ${GREEN}passed${NC}"
        has_sudo=1
    else
        echo -e "  $(printf '%-32s' "• root / sudo:") ${RED}failed${NC} — run with sudo"
        all_passed=1
    fi

    if command -v apt &>/dev/null; then
        echo -e "  $(printf '%-32s' "• apt:") ${GREEN}passed${NC}"
    else
        echo -e "  $(printf '%-32s' "• apt:") ${RED}failed${NC} — apt not found"
        all_passed=1
    fi

    if grep -qi "debian" /etc/os-release 2>/dev/null; then
        local ver
        ver=$(grep -oP 'PRETTY_NAME="\K[^"]+' /etc/os-release)
        echo -e "  $(printf '%-32s' "• distribution:") ${GREEN}passed${NC} ($ver)"
    else
        echo -e "  $(printf '%-32s' "• distribution:") ${RED}failed${NC} — only Debian supported"
        all_passed=1
    fi

    for s in "$@"; do
        suite_configured "$s" && rc=$? || rc=$?
        if [ "$rc" -eq "$SUITE_ALREADY" ]; then
            echo -e "  $(printf '%-31s' "• ${s} in APT:") ${YELLOW}already configured${NC}"
        else
            echo -e "  $(printf '%-32s' "• ${s} in APT:") ${GREEN}not yet added${NC}"
        fi
    done

    echo ""
    return $all_passed
}

# ---------------------------------------------------------------------------
# Parse arguments
# ---------------------------------------------------------------------------
CHECK_MODE=0
SUITES=()

for a in "$@"; do
    if [ "${a:0:2}" = "--" ] && [ "$a" != "--check" ]; then
        echo -e "${RED}Error:${NC} unknown flag '$a'"
        echo "Usage: sudo ./apt-unstable-allow.sh [--check|unstable|testing ...]"
        exit 1
    fi
done

if [ $# -eq 1 ] && [ "$1" = "--check" ]; then
    CHECK_MODE=1
elif [ $# -gt 0 ]; then
    SUITES=("$@")
fi

# ---------------------------------------------------------------------------
# --check mode: pre-flight only, no changes
# ---------------------------------------------------------------------------
if [ "$CHECK_MODE" -eq 1 ]; then
    preflight "unstable" "testing"
    exit $?
fi

# ---------------------------------------------------------------------------
# Interactive prompt
# ---------------------------------------------------------------------------
if [ ${#SUITES[@]} -eq 0 ]; then
    echo -n "Which suites to add? (space-separated, e.g., unstable testing): "
    read -r -a SUITES
    if [ ${#SUITES[@]} -eq 0 ]; then
        echo -e "${RED}Error:${NC} no suites specified"
        exit 1
    fi
fi

# ---------------------------------------------------------------------------
# Validate suites
# ---------------------------------------------------------------------------
for s in "${SUITES[@]}"; do
    if [ "$s" != "unstable" ] && [ "$s" != "testing" ]; then
        echo -e "${RED}Error:${NC} invalid suite '$s' (valid: unstable, testing)"
        exit 1
    fi
done

# ---------------------------------------------------------------------------
# Pre-flight (for requested suites only)
# ---------------------------------------------------------------------------
if ! preflight "${SUITES[@]}"; then
    echo -e "${RED}Pre-flight checks failed. Aborting.${NC}"
    exit 1
fi

# ---------------------------------------------------------------------------
# Add suites to APT sources
# ---------------------------------------------------------------------------
NEEDS_UPDATE=0

for suite in "${SUITES[@]}"; do
    suite_configured "$suite" && rc=$? || rc=$?
    if [ "$rc" -eq "$SUITE_ALREADY" ]; then
        echo -e "${YELLOW}skip${NC} $suite — already configured in APT"
        continue
    fi

    f="/etc/apt/sources.list.d/debian-${suite}.sources"
    echo "Adding ${suite} repository..."
    sudo tee "$f" >/dev/null <<SOURCES_EOF
Types: deb
URIs: http://deb.debian.org/debian
Suites: ${suite}
Components: main
Signed-By: /usr/share/keyrings/debian-archive-keyring.gpg
SOURCES_EOF
    echo -e "${GREEN}+${NC} $f"
    cat "$f" 2>/dev/null || sudo cat "$f"
    echo ""

    NEEDS_UPDATE=1
done

# ---------------------------------------------------------------------------
# APT pinning
# ---------------------------------------------------------------------------
pf="/etc/apt/preferences.d/debian-unstable-testing.pref"
echo "Adding APT pinning..."
{
    echo "# APT pinning for unstable/testing — added by debian-apt-unstable-allow"
    for suite in "${SUITES[@]}"; do
        echo ""
        echo "Package: *"
        echo "Pin: release a=${suite}"
        echo "Pin-Priority: 50"
    done
} | sudo tee "$pf" >/dev/null
echo -e "${GREEN}+${NC} $pf"
echo ""

# ---------------------------------------------------------------------------
# apt update
# ---------------------------------------------------------------------------
if [ "$NEEDS_UPDATE" -eq 1 ]; then
    echo "Updating APT cache..."
    sudo apt update
    echo ""
fi

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
echo "Done."
for s in "${SUITES[@]}"; do
    echo "  added $s (priority 50)"
done
echo ""
echo "To install from these repos:"
for s in "${SUITES[@]}"; do
    echo "  apt install -t $s <package>"
done
