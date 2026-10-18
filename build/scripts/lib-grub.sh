#!/usr/bin/env bash
# Validate the hash before interpolating it into GRUB configuration.

require_grub_password_hash() {
    local password_hash="${1:-}"
    local hash_pattern='^grub\.pbkdf2\.sha512\.[1-9][0-9]*\.([[:xdigit:]]{2})+\.[[:xdigit:]]{128}$'
    if [[ ! "$password_hash" =~ $hash_pattern ]]; then
        echo "GALLOS_GRUB_PASSWORD_HASH must contain a valid GRUB PBKDF2 hash" >&2
        return 1
    fi
}
