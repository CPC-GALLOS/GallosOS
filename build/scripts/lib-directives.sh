#!/usr/bin/env bash

copy_directives_profile() {
    local source_file="$1"
    local staging_dir="$2"
    local config_dir="$staging_dir/gallos/config"

    mkdir -p "$config_dir/baseline"
    rm -f "$config_dir/gallos.toml" "$config_dir/baseline.toml"
    cp "$source_file" "$config_dir/baseline/baseline.gallos.toml"
}

copy_remote_policy_url() {
    local remote_url="$1"
    local staging_dir="$2"
    local source_file="$staging_dir/gallos/config/remote-policy-url.txt"

    rm -f "$source_file"
    if [[ -z "$remote_url" ]]; then
        return 0
    fi
    if [[ ! "$remote_url" =~ ^https://[A-Za-z0-9.-]+(:[0-9]+)?(/[A-Za-z0-9._~:/?\&=+#%-]*)?$ ]]; then
        echo "lib-directives.sh: remote policy URL must be an HTTPS URL" >&2
        return 1
    fi

    mkdir -p "$(dirname "$source_file")"
    printf '%s\n' "$remote_url" > "$source_file"
    chmod 0644 "$source_file"
}
