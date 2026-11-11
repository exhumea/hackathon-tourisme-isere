#!/bin/sh
set -eu

fail() {
    printf '[github-config] %s\n' "$*" >&2
    exit 1
}

# Github part
github_user=$(gh api user --jq .login)
github_auth_keys=$(curl -fsSL "https://github.com/$github_user.keys") ||
    fail "unable to fetch GitHub SSH authentication keys for $github_user."
github_sign_keys=$(gh api "users/$github_user/ssh_signing_keys" --jq '.[].key' 2>/dev/null) ||
    fail "unable to fetch GitHub SSH signing keys for $github_user."

sock=${SSH_AUTH_SOCK:-}
if [ -z "$sock" ]; then
    fail "SSH_AUTH_SOCK is not set."
fi
if [ ! -S "$sock" ]; then
    fail "the SSH agent socket $sock does not exist."
fi

if agent_keys=$(ssh-add -L 2>&1); then
    rc=0
else
    rc=$?
fi

# ssh-add exit 2 is "could not connect at all"; exit 1 is "connected, but
# the exchange failed or the agent is empty". Forwarding being switched off
# can land in either one depending on how far the connection gets, so only
# the genuinely-empty agent gets a recovery of its own -- every other state
# runs the same host-side checks, the forwarding setting first.
case $rc in
    0) ;;
    1)
        case "$agent_keys" in
            *"no identities"*) ;;
            *) fail "the agent did not answer usably (ssh-add: $agent_keys)." ;;
        esac
        ;;
    *) fail "unexpected error for $sock (ssh-add: $agent_keys, exit $rc)." ;;
esac

get_matching_keys() {
    # Get the unique matching key (type + key data, but not the optional comment)
    # Tolerate no matching key
    matches=$(
        while IFS= read -r a_key; do
            [ -z "$a_key" ] && continue
            read -r a_type a_data _ <<EOF
$a_key
EOF
            while IFS= read -r b_key; do
                [ -z "$b_key" ] && continue
                read -r b_type b_data _ <<EOF
$b_key
EOF
                if [ "$a_type" = "$b_type" ] && [ "$a_data" = "$b_data" ]; then
                    echo "$a_type $a_data"
                    break
                fi
            done <<EOF
$1
EOF
        done <<EOF
$agent_keys
EOF
    )

    matches=$(echo "$matches" | sort -u)
    match_count=$(echo "$matches" | grep -c . || true)

    case "$match_count" in
        0) ;; # no match but NOT an error
        1) echo "$matches" ;;
        *) fail "N=$match_count matching keys found in ssh-agent for $2." ;;
    esac
}

matching_auth_key=$(get_matching_keys "$github_auth_keys" "authentication")
matching_sign_key=$(get_matching_keys "$github_sign_keys" "signing")

if [ -n "$matching_auth_key" ]; then
    if [ "$matching_auth_key" = "$matching_sign_key" ]; then
        echo "$matching_auth_key" "auth+sign@$github_user.github"
        exit 0
    else
        echo "$matching_auth_key" "auth@$github_user.github"
    fi
fi
if [ -n "$matching_sign_key" ]; then
    echo "$matching_sign_key" "sign@$github_user.github"
fi
