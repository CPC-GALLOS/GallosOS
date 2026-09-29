#!/usr/bin/env bash
# Runs Stages 1-5b in order inside the gallos-builder container.
# Invoked by ../Makefile; not meant to be run directly on the host.
set -euo pipefail

CONFIG="$1"
DIRECTIVES_PROFILE="${2:-}"
REMOTE_POLICY_URL="${3:-}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT_DIR="/repo/build/output"
ROOTFS="$OUT_DIR/rootfs"
STAGING="$OUT_DIR/staging"
PROFILE_NAME="$(basename "$CONFIG")"
PROFILE_NAME="${PROFILE_NAME%.build.toml}"
PROFILE_NAME="${PROFILE_NAME%.toml}"
ISO="$OUT_DIR/gallosos-$PROFILE_NAME-amd64.iso"

if [[ -n "$DIRECTIVES_PROFILE" ]]; then
    if [[ "$DIRECTIVES_PROFILE" != /* ]]; then
        DIRECTIVES_PROFILE="/repo/$DIRECTIVES_PROFILE"
    fi
    if [[ ! -f "$DIRECTIVES_PROFILE" ]]; then
        echo "run-pipeline.sh: runtime directives profile not found: $DIRECTIVES_PROFILE" >&2
        exit 1
    fi
fi
if [[ -n "$REMOTE_POLICY_URL" && ! "$REMOTE_POLICY_URL" =~ ^https://[A-Za-z0-9.-]+(:[0-9]+)?(/[A-Za-z0-9._~:/?\&=+#%-]*)?$ ]]; then
    echo "run-pipeline.sh: remote policy URL must be an HTTPS URL" >&2
    exit 1
fi

echo "=== Stage 1: Bootstrap ==="
"$SCRIPT_DIR/01-bootstrap.sh" "$CONFIG" "$ROOTFS"

echo "=== Stage 2: Provision ==="
"$SCRIPT_DIR/02-provision.sh" "$CONFIG" "$ROOTFS"

echo "=== Stage 3: Harden ==="
"$SCRIPT_DIR/03-harden.sh" "$CONFIG" "$ROOTFS"

echo "=== Stage 4: Optimize ==="
"$SCRIPT_DIR/04-optimize.sh" "$CONFIG" "$ROOTFS"

echo "=== Stage 5a: Squash ==="
"$SCRIPT_DIR/build-squashfs.sh" "$ROOTFS" "$STAGING"

echo "=== Stage 5b: ISO ==="
"$SCRIPT_DIR/build-iso.sh" "$STAGING" "$ISO" "$DIRECTIVES_PROFILE" "$REMOTE_POLICY_URL"

if [[ "$PROFILE_NAME" == "universal" ]]; then
    ln -sf "gallosos-universal-amd64.iso" "$OUT_DIR/gallos-os-amd64.iso"
fi

echo "=== Done: $ISO ==="
