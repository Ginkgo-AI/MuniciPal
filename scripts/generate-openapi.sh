#!/usr/bin/env bash
set -euo pipefail

# Generate OpenAPI JSON from FastAPI app, then run openapi-ts to produce
# a typed TypeScript client.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

echo "==> Exporting OpenAPI schema from FastAPI..."
python3 -c "
import json
from municipal.web.app import create_app
app = create_app()
schema = app.openapi()
with open('$ROOT_DIR/openapi.json', 'w') as f:
    json.dump(schema, f, indent=2)
print(f'  Written to $ROOT_DIR/openapi.json ({len(schema.get(\"paths\", {}))} paths)')
"

echo "==> Generating TypeScript client..."
cd "$ROOT_DIR/packages/api-client"
pnpm run generate

echo "==> Done!"
