#!/bin/bash
# Usage: $0 <SANDBOX_PORT>

set -euo pipefail

PORT=${PORT:-$1}
ssh_auth_sock=$(find "/tmp/sbx-oc-$PORT-ssh/" -name 'agent.*' -type s)
SSH_AUTH_SOCK="$ssh_auth_sock" exec sbx exec -it "oc-$PORT" /bin/bash -c "opencode pair --url 'http://${HOST:-127.0.0.1}:$PORT'"
