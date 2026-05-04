#!/bin/bash
# Local LinkedIn auto-poster launcher.
# Wakes from launchd schedule, runs the pipeline via Claude CLI headless,
# logs output, exits. Mac sleeps again after.

set -u

cd "$(dirname "$0")"

LOG_DIR="$HOME/Posts/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/run-$(date -u +%Y%m%dT%H%M%SZ).log"

echo "=== START: $(date) ===" | tee -a "$LOG_FILE"

# Cache person ID (skips runtime LinkedIn API lookup)
mkdir -p data
echo 'kdloWK9rIy' > data/.linkedin_person_id

# Pull latest code/state from repo before running
# Clean up stale worktrees that block rebase pull
git worktree prune 2>&1 | tee -a "$LOG_FILE"
rm -rf .claude/worktrees 2>/dev/null || true
git stash 2>&1 | tee -a "$LOG_FILE"
git pull --rebase origin master 2>&1 | tee -a "$LOG_FILE"
git stash pop 2>&1 | tee -a "$LOG_FILE" || true

# Run pipeline via Claude CLI (uses your Claude Code subscription)
PROMPT_FILE="prompts/agent_instructions.md"

echo "=== RUNNING CLAUDE at $(date) ===" | tee -a "$LOG_FILE"

# Prevent sleep mid-run
caffeinate -i -t 600 claude \
  -p "Follow the instructions in $PROMPT_FILE exactly, step by step. Do not skip any step." \
  --dangerously-skip-permissions \
  --output-format text \
  --add-dir "$(pwd)" \
  2>&1 | tee -a "$LOG_FILE"

EXIT_CODE=${PIPESTATUS[0]}
echo "=== EXIT: $EXIT_CODE at $(date -u) ===" | tee -a "$LOG_FILE"
exit $EXIT_CODE
