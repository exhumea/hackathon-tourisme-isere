#!/bin/bash
# Usage: $0 <SANDBOX_PORT>

set -euo pipefail

PORT=${PORT:-$1}
exec sbx exec -it "oc-$PORT" /bin/bash -c "opencode pair --url 'http://${HOST:-127.0.0.1}:$PORT'"
