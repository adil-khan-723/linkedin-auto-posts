# LinkedIn Post Pipeline — Agent Instructions

Run this pipeline every scheduled trigger. Follow steps in order. Do not skip any step.

---

## Step 0: Setup

```bash
pip install -r requirements-prod.txt
```

Wait for install to complete before continuing.

---

## Step 1: Scrape GitHub

```bash
python github_scraper.py
```

Wait for "Scraped N repos" confirmation before continuing.

---

## Step 2: Pick Topic

```bash
python topic_picker.py
```

Wait for "Selected:" confirmation before continuing.

---

## Step 3: Read Selected Topic

Read `data/selected_topic.json`. Note the `topic`, `angle`, and `source` fields.

---

## Step 4: Generate Post Draft

Read `prompts/post_generator.md` carefully. Write a LinkedIn post following all rules in that file, using the topic and angle from Step 3.

---

## Step 5: Humanize

Read `prompts/humanizer_rules.md`. Apply every rule to your draft. Rewrite any sentence that triggers a rule. Output the revised post.

---

## Step 6: Quality Gate

Read `prompts/quality_criteria.md`. Evaluate your humanized post against every criterion.

- If **PASS**: continue to Step 7.
- If **REJECT**: note the reason, rewrite the post (return to Step 4 with the rejection reason in mind). Track retry count.
- After **3 consecutive REJECT results**: write failure entry to `data/run_log.json` (append to runs array):

```json
{
  "date": "<today ISO>",
  "topic": "<selected topic>",
  "source": "<source>",
  "success": false,
  "post_id": null,
  "error": "quality gate failed after 3 retries"
}
```

Then **skip Steps 7-10** and **go directly to Step 11** (so the failure is persisted).

---

## Step 7: Generate Diagram

```bash
python mermaid_generator.py
```

This may print "skipping diagram" — that's fine, continue. If it prints "Diagram saved: data/diagram.png", the poster will auto-attach it.

---

## Step 8: Post to LinkedIn

Run with the exact approved post text:

```bash
python linkedin_poster.py "APPROVED POST TEXT HERE"
```

Replace `APPROVED POST TEXT HERE` with the full post content. Keep all punctuation and line breaks intact.

---

## Step 9: Confirm

Check output for "Posted successfully. ID: ..." confirmation. If you see ERROR, check `data/run_log.json` for details.

---

## Step 9.5: Archive Post

Read `data/selected_topic.json` to get `topic`, `angle`, `source`, `repo`.

1. Create a slug from the topic: lowercase, replace spaces and special chars with hyphens, max 50 chars.
2. Get current UTC timestamp in ISO 8601 format (e.g. `2026-05-05T04:30:00Z`).
3. Determine the archive directory:
   - If `source` is `"github"` → `data/posts/github/YYYY-MM-DD-<slug>/`
   - If `source` is `"self-generated"` → `data/posts/self-generated/YYYY-MM-DD-<slug>/`
4. Create that directory and write these files:

**post.txt** — the exact final approved post text, verbatim.

**meta.json** — write exactly this structure:
```json
{
  "topic": "<topic from selected_topic.json>",
  "angle": "<angle from selected_topic.json>",
  "source": "<source>",
  "repo": "<repo or null>",
  "linkedin_id": "<post ID from Step 9, e.g. urn:li:share:...>",
  "posted_at": "<UTC ISO timestamp>",
  "created_at": "<UTC ISO timestamp of this archive write>"
}
```

**diagram.png** — if `data/diagram.png` exists, copy it into the archive directory. If it doesn't exist, skip silently.

---

## Step 10: Token Expiry Check

Read `data/run_log.json`. Find the most recent entry with `"success": true` and check its `"date"` field. If it was more than 53 days ago (60-day token - 7-day warning), append this warning to `data/run_log.json` runs:

```json
{
  "date": "<today>",
  "topic": null,
  "source": null,
  "success": null,
  "post_id": null,
  "error": "WARNING: LinkedIn access token expires in less than 7 days. Regenerate at https://developer.linkedin.com and update .env"
}
```

---

## Step 11: Save State to GitHub

Push updated state files so run history and posted topics are persisted:

```bash
git config user.email "bot@linkedin-auto-posts"
git config user.name "LinkedIn Bot"

# Embed token in remote URL so push has auth
if [ -n "$GITHUB_TOKEN" ]; then
  git remote set-url origin "https://x-access-token:${GITHUB_TOKEN}@github.com/adil-khan-723/linkedin-auto-posts.git"
fi

git add data/run_log.json data/posted_topics.json data/posts/
git commit -m "chore: update run state [skip ci]" || echo "nothing to commit"

if ! git push 2>&1; then
  echo "=== GIT PUSH FAILED — dumping state to logs ==="
  echo "--- data/run_log.json ---"
  cat data/run_log.json 2>/dev/null || echo "(missing)"
  echo "--- data/posted_topics.json ---"
  cat data/posted_topics.json 2>/dev/null || echo "(missing)"
fi
```

`GITHUB_TOKEN` must be present in `.env` (set in the routine prompt). If push fails, state contents dumped to CCR logs as fallback.
