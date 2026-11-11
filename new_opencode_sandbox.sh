#!/bin/bash
set -euo pipefail

this_dir=$(dirname "$0")

get_free_port() {
    python3 -c '
import socket
s = socket.socket()
s.bind(("127.0.0.1", 0))
print(s.getsockname()[1])
s.close()
'
}

PORT=${PORT:-$(get_free_port)}

# <!> no need of 'user:email' scope on token
gh_token=$(gh auth token -u "$GH_AGENT")
gh_user=$(GH_TOKEN="$gh_token" gh api user --jq '{id, login, name, email}')
git_name=$(jq -r .name <<<"$gh_user")
git_email=$(jq -r '.email // "\(.id)+\(.login)@users.noreply.github.com"' <<<"$gh_user")

# Restricted SSH agent forwarding
needed_keys_full=$(GH_TOKEN="$gh_token" "$this_dir"/get_github_keys.sh)
mapfile -t needed_keys <<<"$(echo "$needed_keys_full" | awk '{print $2}')"
args=()
for key in "${needed_keys[@]}"; do args+=(-k "$key"); done

# no way to control output socket, so we have to change working directory
ssh_dir="/tmp/sbx-oc-${PORT}-ssh"
rm -rf "$ssh_dir" && mkdir "$ssh_dir" && pushd "$ssh_dir"
ssh_auth_sock=$(ssh-agent-filter "${args[@]}" | sed -nE "s/^SSH_AUTH_SOCK='([^']+)';.+/\1/p")
popd

echo SSH_AUTH_SOCK="$ssh_auth_sock"

# Unfortunately SSH_AUTH_SOCK is needed everywhere (even for re-pairing)
SSH_AUTH_SOCK="$ssh_auth_sock" sbx env run --force \
    --env-arg ghUser="$GH_AGENT" \
    --env-arg gitName="$git_name" \
    --env-arg gitEmail="$git_email" \
    --env-arg hostPort="$PORT" \
    --env-arg opencodeApiKey="${OPENCODE_API_KEY:-}" \
    --name "oc-$PORT" --detach &&
    SSH_AUTH_SOCK="$ssh_auth_sock" sbx exec -it "oc-$PORT" /bin/bash -c "opencode pair --url 'http://127.0.0.1:$PORT'"
