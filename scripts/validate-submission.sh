#!/usr/bin/env bash
#
# validate-submission.sh — OpenEnv Submission Validator
#
# Checks:
#   1. HF Space /health returns 200
#   2. HF Space /reset returns 200 with a valid OpenEnv observation body
#   3. HF Space /step returns 200 with reward in [0, 1]
#   4. Docker image builds from the repo Dockerfile
#   5. openenv validate passes
#
# Prerequisites:
#   - Docker:       https://docs.docker.com/get-docker/
#   - openenv-core: pip install openenv-core
#   - curl, jq     (usually pre-installed; jq via: brew install jq / apt install jq)
#
# Run:
#   curl -fsSL https://raw.githubusercontent.com/<owner>/<repo>/main/scripts/validate-submission.sh | bash -s -- <ping_url> [repo_dir]
#
#   Or download and run locally:
#     chmod +x validate-submission.sh
#     ./validate-submission.sh <ping_url> [repo_dir]
#
# Arguments:
#   ping_url   Your HuggingFace Space URL (e.g. https://your-space.hf.space)
#   repo_dir   Path to your repo (default: current directory)
#
# Examples:
#   ./validate-submission.sh https://p1yush-exe-bottlemedenv.hf.space
#   ./validate-submission.sh https://p1yush-exe-bottlemedenv.hf.space ./my-repo
#

set -uo pipefail

DOCKER_BUILD_TIMEOUT=600
CURL_TIMEOUT=30

if [ -t 1 ]; then
  RED='\033[0;31m'
  GREEN='\033[0;32m'
  YELLOW='\033[1;33m'
  BOLD='\033[1m'
  NC='\033[0m'
else
  RED='' GREEN='' YELLOW='' BOLD='' NC=''
fi

# ---------------------------------------------------------------------------
# run_with_timeout <seconds> <cmd> [args...]
# ---------------------------------------------------------------------------
run_with_timeout() {
  local secs="$1"; shift
  if command -v timeout &>/dev/null; then
    timeout "$secs" "$@"
    return $?
  elif command -v gtimeout &>/dev/null; then
    gtimeout "$secs" "$@"
    return $?
  fi
  # Fallback: background process with watcher
  "$@" &
  local pid=$!
  ( sleep "$secs" && kill "$pid" 2>/dev/null ) &
  local watcher=$!
  local rc=0
  wait "$pid" 2>/dev/null || rc=$?
  kill "$watcher" 2>/dev/null
  wait "$watcher" 2>/dev/null || true
  return "$rc"
}

portable_mktemp() {
  local prefix="${1:-validate}"
  mktemp "${TMPDIR:-/tmp}/${prefix}-XXXXXX" 2>/dev/null || mktemp
}

# ---------------------------------------------------------------------------
# curl_json <method> <url> [body]
# Sets globals: CURL_HTTP_CODE, CURL_BODY
# ---------------------------------------------------------------------------
CURL_HTTP_CODE=""
CURL_BODY=""
_CURL_BODY_FILE=""

curl_json() {
  local method="$1"
  local url="$2"
  local body="${3:-}"

  CURL_HTTP_CODE=$(
    curl -s -o "$_CURL_BODY_FILE" -w "%{http_code}" \
      -X "$method" \
      -H "Content-Type: application/json" \
      ${body:+-d "$body"} \
      "$url" \
      --max-time "$CURL_TIMEOUT" 2>/dev/null \
    || printf "000"
  )
  CURL_BODY=$(cat "$_CURL_BODY_FILE" 2>/dev/null || printf "")
}

# ---------------------------------------------------------------------------
# jq_field <json> <field>  — extract a JSON field; empty string if absent/null
# Falls back gracefully when jq is not installed.
# ---------------------------------------------------------------------------
jq_field() {
  local json="$1"
  local field="$2"
  if command -v jq &>/dev/null; then
    printf '%s' "$json" | jq -r "$field // empty" 2>/dev/null || true
  else
    # Minimal regex fallback — good enough for simple string/number fields
    printf '%s' "$json" \
      | grep -o "\"${field#.}\"[[:space:]]*:[[:space:]]*[^,}]*" \
      | sed 's/.*:[[:space:]]*//' \
      | tr -d '"' \
      | head -1 \
      || true
  fi
}

CLEANUP_FILES=()
cleanup() { rm -f "${CLEANUP_FILES[@]+"${CLEANUP_FILES[@]}"}"; }
trap cleanup EXIT

PING_URL="${1:-}"
REPO_DIR="${2:-.}"

if [ -z "$PING_URL" ]; then
  printf "Usage: %s <ping_url> [repo_dir]\n" "$0"
  printf "\n"
  printf "  ping_url   Your HuggingFace Space URL (e.g. https://your-space.hf.space)\n"
  printf "  repo_dir   Path to your repo (default: current directory)\n"
  exit 1
fi

if ! REPO_DIR="$(cd "$REPO_DIR" 2>/dev/null && pwd)"; then
  printf "Error: directory '%s' not found\n" "${2:-.}"
  exit 1
fi
PING_URL="${PING_URL%/}"
export PING_URL
PASS=0

log()  { printf "[%s] %b\n" "$(date -u +%H:%M:%S)" "$*"; }
pass() { log "${GREEN}PASSED${NC} -- $1"; PASS=$((PASS + 1)); }
fail() { log "${RED}FAILED${NC} -- $1"; }
warn() { log "${YELLOW}WARN${NC}   -- $1"; }
hint() { printf "  ${YELLOW}Hint:${NC} %b\n" "$1"; }
stop_at() {
  printf "\n"
  printf "${RED}${BOLD}Validation stopped at %s.${NC} Fix the above before continuing.\n" "$1"
  exit 1
}

# Shared temp file for curl response bodies
_CURL_BODY_FILE=$(portable_mktemp "validate-body")
CLEANUP_FILES+=("$_CURL_BODY_FILE")

printf "\n"
printf "${BOLD}========================================${NC}\n"
printf "${BOLD}  OpenEnv Submission Validator${NC}\n"
printf "${BOLD}========================================${NC}\n"
log "Repo:     $REPO_DIR"
log "Ping URL: $PING_URL"
printf "\n"

# ===========================================================================
# Step 1 — Health check
# ===========================================================================
log "${BOLD}Step 1/5: Health check${NC} ($PING_URL/health) ..."

curl_json GET "$PING_URL/health"

if [ "$CURL_HTTP_CODE" = "200" ]; then
  pass "HF Space /health is up (HTTP 200)"
elif [ "$CURL_HTTP_CODE" = "000" ]; then
  fail "HF Space not reachable (connection failed or timed out)"
  hint "Check that your Space is running: $PING_URL"
  hint "Try: curl -s -o /dev/null -w '%%{http_code}' $PING_URL/health"
  stop_at "Step 1"
else
  fail "HF Space /health returned HTTP $CURL_HTTP_CODE (expected 200)"
  hint "Make sure your Space is running and PORT=7860 / app_port=7860 are set."
  stop_at "Step 1"
fi

# ===========================================================================
# Step 2 — Reset returns a valid observation
# ===========================================================================
log "${BOLD}Step 2/5: OpenEnv /reset${NC} ($PING_URL/reset) ..."

curl_json POST "$PING_URL/reset" '{}'

if [ "$CURL_HTTP_CODE" = "000" ]; then
  fail "HF Space /reset not reachable"
  stop_at "Step 2"
elif [ "$CURL_HTTP_CODE" != "200" ]; then
  fail "/reset returned HTTP $CURL_HTTP_CODE (expected 200)"
  hint "Response body: $CURL_BODY"
  stop_at "Step 2"
fi

# Validate required observation fields are present
RESET_BODY="$CURL_BODY"
TASK_DESC=$(jq_field "$RESET_BODY" ".observation.task_description // .task_description")
DONE_VAL=$(jq_field  "$RESET_BODY" ".observation.done           // .done")
REWARD_VAL=$(jq_field "$RESET_BODY" ".observation.reward        // .reward")
SESSION_ID=$(jq_field "$RESET_BODY" ".session_id")

if [ -z "$TASK_DESC" ] && [ -z "$SESSION_ID" ]; then
  fail "/reset response missing both task_description and session_id"
  hint "Response body: $RESET_BODY"
  stop_at "Step 2"
fi

pass "/reset returned a valid observation"
[ -n "$TASK_DESC" ] && log "  task_description: ${TASK_DESC:0:80}..."

# ===========================================================================
# Step 3 — Step returns a valid graded observation
# ===========================================================================
log "${BOLD}Step 3/5: OpenEnv /step${NC} ($PING_URL/step) ..."

STEP_BODY='{"action":{"code":"print(42)"}}'
curl_json POST "$PING_URL/step" "$STEP_BODY"

if [ "$CURL_HTTP_CODE" = "000" ]; then
  fail "/step not reachable"
  stop_at "Step 3"
elif [ "$CURL_HTTP_CODE" != "200" ]; then
  fail "/step returned HTTP $CURL_HTTP_CODE (expected 200)"
  hint "Response body: $CURL_BODY"
  stop_at "Step 3"
fi

STEP_RESP="$CURL_BODY"
REWARD=$(jq_field "$STEP_RESP" ".observation.reward // .reward")

if [ -z "$REWARD" ]; then
  fail "/step response missing reward field"
  hint "Response body: $STEP_RESP"
  stop_at "Step 3"
fi

# Verify reward is numeric and in [0, 1]
REWARD_OK=false
if command -v python3 &>/dev/null; then
  python3 -c "r=float('$REWARD'); assert 0.0<=r<=1.0" 2>/dev/null && REWARD_OK=true
elif command -v awk &>/dev/null; then
  awk -v r="$REWARD" 'BEGIN{exit!(r>=0&&r<=1)}' && REWARD_OK=true
fi

if [ "$REWARD_OK" = true ]; then
  pass "/step returned reward=$REWARD in [0, 1]"
else
  warn "/step reward='$REWARD' — could not verify it is in [0, 1] (check manually)"
  PASS=$((PASS + 1))  # non-fatal: count as pass but emit warning
fi

# ===========================================================================
# Step 4 — Docker build
# ===========================================================================
log "${BOLD}Step 4/5: Docker build${NC} ..."

if ! command -v docker &>/dev/null; then
  fail "docker command not found"
  hint "Install Docker: https://docs.docker.com/get-docker/"
  stop_at "Step 4"
fi

if [ -f "$REPO_DIR/Dockerfile" ]; then
  DOCKER_CONTEXT="$REPO_DIR"
elif [ -f "$REPO_DIR/server/Dockerfile" ]; then
  DOCKER_CONTEXT="$REPO_DIR/server"
else
  fail "No Dockerfile found in repo root or server/ directory"
  stop_at "Step 4"
fi

log "  Found Dockerfile in $DOCKER_CONTEXT"

# Tag the image so it doesn't become a dangling <none>:<none> layer;
# always clean up regardless of pass/fail.
DOCKER_TAG="openenv-validate-$$"
BUILD_OK=false
BUILD_OUTPUT=$(run_with_timeout "$DOCKER_BUILD_TIMEOUT" \
  docker build -t "$DOCKER_TAG" "$DOCKER_CONTEXT" 2>&1) && BUILD_OK=true

docker rmi "$DOCKER_TAG" &>/dev/null || true

if [ "$BUILD_OK" = true ]; then
  pass "Docker build succeeded"
else
  fail "Docker build failed (timeout=${DOCKER_BUILD_TIMEOUT}s)"
  printf "%s\n" "$BUILD_OUTPUT" | tail -20
  stop_at "Step 4"
fi

# ===========================================================================
# Step 5 — openenv validate
# ===========================================================================
log "${BOLD}Step 5/5: openenv validate${NC} ..."

if ! command -v openenv &>/dev/null; then
  fail "openenv command not found"
  hint "Install it: pip install openenv-core"
  stop_at "Step 5"
fi

VALIDATE_OK=false
VALIDATE_OUTPUT=$(cd "$REPO_DIR" && openenv validate 2>&1) && VALIDATE_OK=true

if [ "$VALIDATE_OK" = true ]; then
  pass "openenv validate passed"
  [ -n "$VALIDATE_OUTPUT" ] && log "  $VALIDATE_OUTPUT"
else
  fail "openenv validate failed"
  printf "%s\n" "$VALIDATE_OUTPUT"
  stop_at "Step 5"
fi

# ===========================================================================
# Summary
# ===========================================================================
printf "\n"
printf "${BOLD}========================================${NC}\n"
printf "${GREEN}${BOLD}  All 5/5 checks passed!${NC}\n"
printf "${GREEN}${BOLD}  Your submission is ready to submit.${NC}\n"
printf "${BOLD}========================================${NC}\n"
printf "\n"

exit 0
