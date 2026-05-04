# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

Fully autonomous LinkedIn post scheduler. Posts DevOps content 3x/week (Mon/Wed/Fri 10am IST) with zero manual involvement. Pipeline runs on the user's Mac via `launchd` + `run_local.sh`, using Claude Code CLI headless mode to orchestrate each run.

## How a Run Works

```
launchd fires run_local.sh at 10am IST
  → git pull latest state
  → claude -p "Follow prompts/agent_instructions.md step by step"
     Step 0: pip install -r requirements-prod.txt
     Step 1: python github_scraper.py      → data/scraped_data.json
     Step 2: python topic_picker.py        → data/selected_topic.json
     Step 3-6: Claude reads topic, writes post, humanizes, quality gates (3 retries)
     Step 7: python mermaid_generator.py   → data/diagram.png (skips if topic not visual)
     Step 8: python linkedin_poster.py "POST TEXT"
               → uploads diagram if present, posts to LinkedIn ugcPosts API
               → appends to data/run_log.json + data/posted_topics.json
     Step 9: Token expiry check
     Step 11: git push state files to GitHub
```

The agent (Claude) generates the post text itself — `post_generator.md`, `humanizer_rules.md`, and `quality_criteria.md` are prompt files Claude reads during the run, not Python code.

## Commands

```bash
# Setup
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Run tests
pytest tests/ -v

# Run single test
pytest tests/test_topic_picker.py::test_pick_topic_falls_back_to_self_generated_when_all_used -v

# Dry run (no post)
python github_scraper.py
python topic_picker.py
cat data/selected_topic.json

# Generate diagram only
python mermaid_generator.py

# Full pipeline (posts for real)
bash run_local.sh
```

## Architecture

### State files (persistent, committed to GitHub)
- `data/posted_topics.json` — every topic ever posted; dedup source for `topic_picker.py`
- `data/run_log.json` — per-run history; checked for token expiry warning

### State files (ephemeral, per run)
- `data/scraped_data.json` — latest GitHub scrape
- `data/selected_topic.json` — current run's topic; read by `mermaid_generator.py` and `linkedin_poster.py`
- `data/diagram.png` — rendered diagram PNG; presence triggers image upload in `linkedin_poster.py`

### Topic selection priority
1. GitHub repos from `DEVOPS_REPOS` list in `github_scraper.py` — filtered against `posted_topics.json`
2. `SELF_GENERATED_TOPICS` list in `topic_picker.py` — used when all GitHub topics exhausted
3. Self-generated topics recycle when all used

### Diagram pipeline
`mermaid_generator.py` generates Mermaid syntax from the topic (heuristic keyword matching → selects diagram type), renders via `mermaid.ink` free API, saves to `data/diagram.png`. `linkedin_poster.py` checks for the file at runtime: if present, calls `linkedin_image_uploader.py` to register + upload via LinkedIn assets API, then attaches the asset URN to the `ugcPosts` payload. If render/upload fails, posts text-only silently.

### LinkedIn API
- Endpoint: `POST https://api.linkedin.com/v2/ugcPosts`
- Auth: Bearer token from `.env` (`LINKEDIN_ACCESS_TOKEN`)
- Token expires every 60 days. Warning logged to `data/run_log.json` at 53 days.
- Required scopes: `w_member_social`, `openid`, `profile`, `email`
- Person ID cached in `data/.linkedin_person_id` (gitignored) — avoids API call each run

### Schedule (Mac launchd)
- Plist: `~/Library/LaunchAgents/com.linkedin.bot.plist`
- Mac auto-wakes 9:55am IST via `pmset repeat wakeorpoweron MWF 09:55:00`
- Mac must be in **sleep** (not shut down) on Sun/Tue/Thu nights for wake to trigger
- Logs per run: `logs/run-<timestamp>.log`

## Credentials (.env)

```
LINKEDIN_CLIENT_ID=...
LINKEDIN_ACCESS_TOKEN=...   # expires every 60 days
LINKEDIN_PERSON_ID=...      # static, also cached in data/.linkedin_person_id
GITHUB_TOKEN=...            # fine-grained PAT, Contents read+write, for git push in Step 11
```

## Token Renewal (every ~53 days)

1. [LinkedIn Developer Portal](https://developer.linkedin.com) → generate new token with all 4 scopes
2. Update `LINKEDIN_ACCESS_TOKEN` in `.env`
3. Wait ~30 min for LinkedIn scope propagation before testing

## Tests

All tests use `monkeypatch` to redirect data file paths to `tmp_path` — no real API calls, no filesystem side effects. `linkedin_poster.py` tests mock `requests.post/get`. `test_post_to_linkedin_sends_correct_payload` verifies the exact ugcPosts payload shape — update it if the payload structure changes.

Note: `test_post_to_linkedin_sends_correct_payload` will need updating if image upload logic changes, since `_try_upload_diagram` is called internally and checks for `data/diagram.png`.
