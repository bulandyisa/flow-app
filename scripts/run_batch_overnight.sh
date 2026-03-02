#!/bin/bash
# Batch runner with failover — if one account fails, tasks go to the other
# 2 бота: account 1 (Акк 1, .session), account 2 (Акк 2, .session_2)

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

if [ -x "/tmp/pw_venv/bin/python3" ]; then
    PYTHON="/tmp/pw_venv/bin/python3"
else
    PYTHON="$PROJECT_DIR/venv/bin/python3"
fi
BOT="$SCRIPT_DIR/flow_bot_v2.py"

PAUSE_OK=30        # pause between successful generations
PAUSE_FAIL=60      # pause after failure before retry
MAX_RETRIES=2      # retries per clip on same account

log() { echo "[$(date '+%H:%M:%S')] $*"; }

run_bot() {
    local clip="$1" component="$2" account="$3"
    log "Starting: $clip / $component (account $account)"
    PYTHONUNBUFFERED=1 timeout 600 "$PYTHON" -u "$BOT" \
        --review --clip "$clip" --component "$component" --account "$account" 2>&1
    return $?
}

# Run a task with failover: try primary account, if all retries fail, try the other
run_with_failover() {
    local clip="$1" component="$2" primary="$3" check_glob="$4"

    # Try primary account
    for try in $(seq 1 $MAX_RETRIES); do
        run_bot "$clip" "$component" "$primary"

        if ls $check_glob 2>/dev/null | head -1 | grep -q .; then
            log "OK: $clip $component done (account $primary)"
            sleep $PAUSE_OK
            return 0
        fi
        log "FAIL: $clip $component attempt $try/$MAX_RETRIES (account $primary)"
        [ "$try" -lt "$MAX_RETRIES" ] && sleep $PAUSE_FAIL
    done

    # Failover to other account
    local fallback
    [ "$primary" -eq 1 ] && fallback=2 || fallback=1
    log "FAILOVER: $clip $component → account $fallback"

    for try in $(seq 1 $MAX_RETRIES); do
        run_bot "$clip" "$component" "$fallback"

        if ls $check_glob 2>/dev/null | head -1 | grep -q .; then
            log "OK: $clip $component done (account $fallback, failover)"
            sleep $PAUSE_OK
            return 0
        fi
        log "FAIL: $clip $component failover attempt $try/$MAX_RETRIES (account $fallback)"
        [ "$try" -lt "$MAX_RETRIES" ] && sleep $PAUSE_FAIL
    done

    log "GIVE UP: $clip $component — both accounts failed"
    return 1
}

# ── Phase 1: VEO for clips with keyframes ──
VEO_CLIPS="S01_C S02_B S02_C S02_D S03_D S03_E"
log "=== Phase 1: VEO generation ==="
for clip in $VEO_CLIPS; do
    if ls "$PROJECT_DIR/output/review/$clip/veo/"*/variant_1.mp4 2>/dev/null | head -1 | grep -q .; then
        log "SKIP $clip — already has VEO"
        continue
    fi
    run_with_failover "$clip" "veo" 1 \
        "$PROJECT_DIR/output/review/$clip/veo/*/variant_1.mp4"
done

# ── Phase 2: Keyframes for unblocked clips ──
NB_CLIPS="S06_E S08_C S10_A S10_B S10_C S10_D"
log "=== Phase 2: Keyframe generation ==="
for clip in $NB_CLIPS; do
    # nb_first
    if [ -f "$PROJECT_DIR/output/frames/${clip}_first.png" ]; then
        log "SKIP $clip nb_first — already accepted"
    else
        run_with_failover "$clip" "nb_first" 2 \
            "$PROJECT_DIR/output/review/$clip/nb_first/*/variant_1.png"
    fi

    # nb_last
    if [ -f "$PROJECT_DIR/output/frames/${clip}_last.png" ]; then
        log "SKIP $clip nb_last — already accepted"
    else
        run_with_failover "$clip" "nb_last" 2 \
            "$PROJECT_DIR/output/review/$clip/nb_last/*/variant_1.png"
    fi
done

# ── Phase 3: VEO for newly generated keyframes ──
log "=== Phase 3: VEO for new keyframes ==="
for clip in $NB_CLIPS; do
    if ls "$PROJECT_DIR/output/review/$clip/veo/"*/variant_1.mp4 2>/dev/null | head -1 | grep -q .; then
        log "SKIP $clip — already has VEO"
        continue
    fi
    if ! ls "$PROJECT_DIR/output/review/$clip/nb_first/"*/variant_1.png 2>/dev/null | head -1 | grep -q .; then
        log "SKIP $clip VEO — no first keyframe"
        continue
    fi
    run_with_failover "$clip" "veo" 1 \
        "$PROJECT_DIR/output/review/$clip/veo/*/variant_1.mp4"
done

log "=== ALL DONE ==="
log "Pushing final state to git..."
cd "$PROJECT_DIR"
git add output/review/ output/frames/ output/status.json 2>/dev/null
git commit -m "Batch: generate VEO, keyframes" 2>/dev/null
git push origin master 2>/dev/null
log "Push complete."
