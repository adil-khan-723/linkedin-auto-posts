#!/usr/bin/env python3
"""
Full LinkedIn post pipeline using Anthropic API (Haiku).
Replaces the Claude CLI headless approach for GitHub Actions.
"""

import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import anthropic

MODEL = "claude-haiku-4-5-20251001"
client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])


def log(msg):
    ts = datetime.now(timezone.utc).strftime("%H:%M:%SZ")
    print(f"[{ts}] {msg}", flush=True)


def ask(prompt, system=None):
    kwargs = {"model": MODEL, "max_tokens": 2048, "messages": [{"role": "user", "content": prompt}]}
    if system:
        kwargs["system"] = system
    response = client.messages.create(**kwargs)
    return response.content[0].text.strip()


def read_file(path):
    return Path(path).read_text().strip()


def write_file(path, content):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(content)


# ── Phase 1: Scrape + pick topic ──────────────────────────────────────────────

log("PHASE 1: scrape + pick topic")

subprocess.run([sys.executable, "github_scraper.py"], check=True)
log("GitHub scraped")

subprocess.run([sys.executable, "topic_picker.py"], check=True)
log("Topic picked")

selected = json.loads(read_file("data/selected_topic.json"))
topic = selected["topic"]
angle = selected["angle"]
source = selected["source"]
repo = selected.get("repo")
log(f"Topic: {topic} (source: {source})")

# ── Phase 2: Write post ────────────────────────────────────────────────────────

log("PHASE 2: write post")

post_generator_rules = read_file("prompts/post_generator.md")
humanizer_rules = read_file("prompts/humanizer_rules.md")
quality_criteria = read_file("prompts/quality_criteria.md")

topic_context = f"Topic: {topic}\nAngle: {angle}"

MAX_RETRIES = 3
approved_post = None

for attempt in range(1, MAX_RETRIES + 1):
    log(f"Writing draft (attempt {attempt})")

    draft = ask(
        f"{post_generator_rules}\n\n---\n\n{topic_context}",
    )
    log("Draft written")

    humanized = ask(
        f"{humanizer_rules}\n\n---\n\nPost to review:\n\n{draft}",
    )
    log("Humanized")

    verdict = ask(
        f"{quality_criteria}\n\n---\n\nPost to evaluate:\n\n{humanized}",
    )
    log(f"Quality gate: {verdict[:60]}")

    if verdict.strip() == "PASS":
        approved_post = humanized
        log("Quality gate PASSED")
        break
    else:
        log(f"Quality gate REJECTED (attempt {attempt}): {verdict}")

if not approved_post:
    log("Quality gate failed after 3 retries — writing failure to run_log.json")
    run_log_path = Path("data/run_log.json")
    run_log = json.loads(run_log_path.read_text()) if run_log_path.exists() else {"runs": []}
    run_log["runs"].append({
        "date": datetime.now(timezone.utc).isoformat(),
        "topic": topic,
        "source": source,
        "success": False,
        "post_id": None,
        "error": "quality gate failed after 3 retries",
    })
    write_file("data/run_log.json", json.dumps(run_log, indent=2))
    sys.exit(1)

write_file("data/approved_post.txt", approved_post)

# ── Phase 3: Diagram ───────────────────────────────────────────────────────────

log("PHASE 3: diagram")
result = subprocess.run([sys.executable, "mermaid_generator.py"], capture_output=True, text=True)
print(result.stdout)
if "Diagram saved" in result.stdout:
    log("Diagram generated")
else:
    log("Diagram skipped")

# ── Phase 4: Post to LinkedIn ──────────────────────────────────────────────────

log("PHASE 4: post to LinkedIn")
result = subprocess.run(
    [sys.executable, "linkedin_poster.py", approved_post],
    capture_output=True, text=True
)
print(result.stdout)
print(result.stderr, file=sys.stderr)

if result.returncode != 0:
    log(f"linkedin_poster.py failed (exit {result.returncode})")
    sys.exit(1)

# Extract LinkedIn post ID from output
linkedin_id = None
for line in result.stdout.splitlines():
    if "Posted successfully. ID:" in line:
        linkedin_id = line.split("ID:")[-1].strip()
        break

if not linkedin_id:
    log("WARNING: could not parse LinkedIn post ID from output")

log(f"Posted: {linkedin_id}")

# ── Phase 5: Archive post ──────────────────────────────────────────────────────

log("PHASE 5: archive post")

now_utc = datetime.now(timezone.utc)
date_str = now_utc.strftime("%Y-%m-%d")
slug = topic.lower()
for ch in " /\\:*?\"<>|.,!@#$%^&()[]{}":
    slug = slug.replace(ch, "-")
while "--" in slug:
    slug = slug.replace("--", "-")
slug = slug.strip("-")[:50]

subdir = "github" if source == "github" else "self-generated"
archive_dir = Path(f"data/posts/{subdir}/{date_str}-{slug}")
archive_dir.mkdir(parents=True, exist_ok=True)

write_file(archive_dir / "post.txt", approved_post)

meta = {
    "topic": topic,
    "angle": angle,
    "source": source,
    "repo": repo,
    "linkedin_id": linkedin_id,
    "posted_at": now_utc.isoformat(),
    "created_at": now_utc.isoformat(),
}
write_file(archive_dir / "meta.json", json.dumps(meta, indent=2))

diagram_src = Path("data/diagram.png")
if diagram_src.exists():
    shutil.copy(diagram_src, archive_dir / "diagram.png")
    log("Diagram archived")

log(f"Archived to {archive_dir}")

# ── Phase 6: Token expiry check ───────────────────────────────────────────────

log("PHASE 6: token expiry check")
run_log_path = Path("data/run_log.json")
run_log = json.loads(run_log_path.read_text()) if run_log_path.exists() else {"runs": []}

success_runs = [r for r in run_log.get("runs", []) if r.get("success") is True]
if success_runs:
    last_success_date = success_runs[-1]["date"]
    try:
        last_dt = datetime.fromisoformat(last_success_date.replace("Z", "+00:00"))
        days_ago = (now_utc - last_dt).days
        if days_ago > 53:
            run_log["runs"].append({
                "date": now_utc.isoformat(),
                "topic": None,
                "source": None,
                "success": None,
                "post_id": None,
                "error": "WARNING: LinkedIn access token expires in less than 7 days. Regenerate at https://developer.linkedin.com and update secrets.",
            })
            log("WARNING: token expiry warning added")
    except Exception:
        pass

# Append success entry
run_log["runs"].append({
    "date": now_utc.isoformat(),
    "topic": topic,
    "source": source,
    "success": True,
    "post_id": linkedin_id,
    "error": None,
})
write_file("data/run_log.json", json.dumps(run_log, indent=2))

log("=== PIPELINE COMPLETE ===")
