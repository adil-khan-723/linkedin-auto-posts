# LinkedIn Post Pipeline — Agent Instructions

Run this pipeline every scheduled trigger. Follow steps in order. Do not skip any step.

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
- After **3 consecutive REJECT results**: write failure to `data/run_log.json` with `"success": false` and `"error": "quality gate failed after 3 retries"`, then stop.

---

## Step 7: Post to LinkedIn

Run with the exact approved post text:

```bash
python linkedin_poster.py "APPROVED POST TEXT HERE"
```

Replace `APPROVED POST TEXT HERE` with the full post content. Keep all punctuation and line breaks intact.

---

## Step 8: Confirm

Check output for "Posted successfully. ID: ..." confirmation. If you see ERROR, check `data/run_log.json` for details.

---

## Step 9: Token Expiry Check

Read `data/run_log.json`. Find the most recent entry with `"success": true` and check its `"posted_at"` date. If it was more than 53 days ago (60-day token - 7-day warning), append this warning to `data/run_log.json` runs:

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
