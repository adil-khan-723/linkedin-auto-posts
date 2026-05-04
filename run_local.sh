#!/bin/bash
# Local LinkedIn auto-poster launcher.
# Wakes from launchd schedule, runs the pipeline via Claude CLI headless,
# logs output, exits. Mac sleeps again after.

set -u

cd "$(dirname "$0")"

LOG_DIR="$HOME/Posts/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/run-$(TZ='Asia/Kolkata' date +%Y%m%dT%H%M%SIST).log"

log() { echo "[$(TZ='Asia/Kolkata' date +%H:%M:%S)] IST $*" | tee -a "$LOG_FILE"; }

log "=== START ==="

# Cache person ID (skips runtime LinkedIn API lookup)
mkdir -p data
echo 'kdloWK9rIy' > data/.linkedin_person_id

# Pull latest code/state from repo before running
log "--- git: pruning worktrees ---"
git worktree prune 2>&1 | tee -a "$LOG_FILE"
rm -rf .claude/worktrees 2>/dev/null || true
git stash 2>&1 | tee -a "$LOG_FILE"
git pull --rebase origin master 2>&1 | tee -a "$LOG_FILE"
git stash pop 2>&1 | tee -a "$LOG_FILE" || true
log "--- git: up to date ---"

run_claude() {
  local PHASE="$1"
  local PROMPT="$2"
  log "--- PHASE: $PHASE ---"
  caffeinate -i -t 600 claude \
    -p "$PROMPT" \
    --dangerously-skip-permissions \
    --output-format text \
    --add-dir "$(pwd)" \
    2>&1 | tee -a "$LOG_FILE"
  local CODE=${PIPESTATUS[0]}
  if [ $CODE -ne 0 ]; then
    log "--- PHASE FAILED: $PHASE (exit $CODE) ---"
    log "=== EXIT: $CODE ==="
    exit $CODE
  fi
  log "--- PHASE DONE: $PHASE ---"
}

# Phase 1: Setup + scrape + pick topic
run_claude "setup+scrape+topic" "$(cat <<'EOF'
Follow these steps exactly, in order:

Step 0: Run: pip install -r requirements-prod.txt
Wait for it to complete.

Step 1: Run: python github_scraper.py
Wait for "Scraped N repos" confirmation.

Step 2: Run: python topic_picker.py
Wait for "Selected:" confirmation.

Output a single line when done: "PHASE 1 COMPLETE: <selected topic>"
EOF
)"

# Phase 2: Write post + humanize + quality gate
run_claude "write+humanize+quality" "$(cat <<'EOF'
Follow these steps exactly, in order:

Step 3: Read data/selected_topic.json. Note the topic, angle, and source fields.

Step 4: Read prompts/post_generator.md carefully. Write a LinkedIn post following all rules in that file.

Step 5: Read prompts/humanizer_rules.md. Apply every rule to your draft. Rewrite any sentence that triggers a rule.

Step 6: Read prompts/quality_criteria.md. Evaluate your humanized post against every criterion.
- If PASS: write the final post text to data/approved_post.txt and output "QUALITY GATE: PASS"
- If REJECT: rewrite and retry up to 3 times.
- After 3 consecutive REJECTs: write failure to data/run_log.json and output "QUALITY GATE: FAILED" then stop.

Output a single line when done: "PHASE 2 COMPLETE: PASS" or "PHASE 2 COMPLETE: FAILED"
EOF
)"

# Phase 3: Diagram generation
run_claude "diagram" "$(cat <<'EOF'
Step 7: Run: python mermaid_generator.py
This may print "skipping diagram" — that is fine.
Output a single line when done: "PHASE 3 COMPLETE: diagram generated" or "PHASE 3 COMPLETE: diagram skipped"
EOF
)"

# Phase 4: Post to LinkedIn
run_claude "post+archive" "$(cat <<'EOF'
Follow these steps exactly, in order:

Step 8: Read data/approved_post.txt to get the approved post text.
Run: python linkedin_poster.py "<exact post text from approved_post.txt>"
Keep all punctuation and line breaks intact.

Step 9: Check output for "Posted successfully. ID: ..." confirmation.

Step 9.5: Archive the post:
- Read data/selected_topic.json for topic, angle, source, repo.
- Create slug: lowercase topic, replace spaces/special chars with hyphens, max 50 chars.
- Get current UTC timestamp in ISO 8601 format.
- If source is "github" → create dir data/posts/github/YYYY-MM-DD-<slug>/
- If source is "self-generated" → create dir data/posts/self-generated/YYYY-MM-DD-<slug>/
- Write post.txt (exact post text verbatim)
- Write meta.json: {"topic":..., "angle":..., "source":..., "repo":..., "linkedin_id":..., "posted_at":..., "created_at":...}
- If data/diagram.png exists, copy it into the archive dir.

Step 10: Read data/run_log.json. If most recent success entry date is more than 53 days ago, append token expiry warning entry.

Output a single line when done: "PHASE 4 COMPLETE: <linkedin post ID>"
EOF
)"

# Phase 5: Push state to GitHub
log "--- PHASE: push-state ---"
git config user.email "bot@linkedin-auto-posts"
git config user.name "LinkedIn Bot"

if [ -n "${GITHUB_TOKEN:-}" ]; then
  git remote set-url origin "https://x-access-token:${GITHUB_TOKEN}@github.com/adil-khan-723/linkedin-auto-posts.git"
fi

git add data/run_log.json data/posted_topics.json data/posts/ 2>&1 | tee -a "$LOG_FILE"
git commit -m "chore: update run state [skip ci]" 2>&1 | tee -a "$LOG_FILE" || log "nothing to commit"

if ! git push 2>&1 | tee -a "$LOG_FILE"; then
  log "=== GIT PUSH FAILED — dumping state to logs ==="
  cat data/run_log.json 2>/dev/null || echo "(missing)"
  cat data/posted_topics.json 2>/dev/null || echo "(missing)"
fi

log "--- PHASE DONE: push-state ---"
log "=== EXIT: 0 ==="
exit 0
