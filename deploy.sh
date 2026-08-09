#!/usr/bin/env bash
set -euo pipefail

# Keep one production deployment implementation so certificate, Nginx and
# systemd settings cannot drift between the documented entry points.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec bash "$SCRIPT_DIR/deploy-prod.sh"
