#!/usr/bin/env bash
# Install pre-commit hooks for the backend (ruff).
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOOKS_DIR="$ROOT_DIR/.git/hooks"

if [[ ! -d "$HOOKS_DIR" ]]; then
  echo "No .git/hooks directory — are you in a git repo?" >&2
  exit 1
fi

if ! command -v uv >/dev/null 2>&1; then
  echo "uv not found. Install: https://docs.astral.sh/uv/" >&2
  exit 1
fi

cat > "$HOOKS_DIR/pre-commit" <<'HOOK'
#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(git rev-parse --show-toplevel)"
cd "$ROOT_DIR/backend"
uv run ruff check src tests
HOOK

chmod +x "$HOOKS_DIR/pre-commit"
echo "Installed pre-commit hook: 'uv run ruff check src tests' (backend/)"
