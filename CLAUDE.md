# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

Fully autonomous LinkedIn post scheduler. Posts DevOps content 2x/week (Mon/Fri 10am IST) with zero manual involvement. Scheduled by GitHub Actions (`.github/workflows/post.yml`) running `pipeline.py` on a GitHub-hosted runner — chosen specifically so Anthropic tokens are spent only on content generation, never on orchestration (see "Schedule" below).

## How a Run Works

```
GitHub Actions cron fires post.yml at 10am IST (Mon/Fri)
  → pip install -r requirements-prod.txt anthropic
  → python pipeline.py
     Phase 1: python github_scraper.py, python topic_picker.py (no LLM)
     Phase 2: draft → humanize → quality gate (3 retries) — 3 Anthropic API
              calls per attempt, model claude-haiku-4-5, prompts read from
              prompts/post_generator.md, humanizer_rules.md, quality_criteria.md
     Phase 3: python mermaid_generator.py               → data/diagram.png (skips if not visual)
     Phase 4: python linkedin_poster.py <approved text>  → posts to LinkedIn ugcPosts API
              → appends to data/run_log.json + data/posted_topics.json
     Phase 5: archive post text + meta.json under data/posts/
     Phase 6: token expiry check
  → commit + push state files to GitHub
```

Only Phase 2 calls the Anthropic API. Every other phase is plain Python/subprocess — no LLM, no tokens spent.

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

### Schedule (GitHub Actions)
- `.github/workflows/post.yml` cron, Mon/Fri 4:30 UTC (10am IST), runs `pipeline.py` on a GitHub-hosted runner — no Mac required, no Claude Code orchestration cost.
- Secrets required in the repo: `ANTHROPIC_API_KEY`, `LINKEDIN_ACCESS_TOKEN`, `LINKEDIN_CLIENT_ID`.
- The local `launchd` plist (`~/Library/LaunchAgents/com.linkedin.bot.plist.disabled`) and the Anthropic cloud routine (`trig_01CdA8YWa1EAGbHtxVAi5KNx`) are both disabled/paused — they ran the full pipeline through Claude Code's agentic loop (`prompts/agent_instructions.md`), burning tokens on mechanical steps as well as content generation, and firing independently caused duplicate/irregular posts. Do not re-enable either without disabling this cron first, to keep a single scheduler.

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
