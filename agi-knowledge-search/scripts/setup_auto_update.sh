#!/usr/bin/env bash
set -euo pipefail

# AGI Knowledge Index Auto-Updater
# Rebuilds the FAISS vector store every 6 hours

SERVICE_DIR=/config/s6-services/knowledge-index-updater

mkdir -p "$SERVICE_DIR"

cat > "$SERVICE_DIR/run" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

LOG="/config/.local/state/futodama/knowledge-index-updater.log"
mkdir -p "$(dirname "$LOG")"
exec >>"$LOG" 2>&1

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] knowledge-index-updater started"

while true; do
    echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Rebuilding vector store..."
    cd /config/.openclaw/workspace
    uv run skills/agi-knowledge-search/scripts/vector_store.py rebuild 2>&1 || true
    echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Rebuild complete. Sleeping 6h..."
    sleep 21600
done
EOF

chmod +x "$SERVICE_DIR/run"
echo "✅ Created s6 service: $SERVICE_DIR"
echo "Run 'docker compose restart' to activate"
