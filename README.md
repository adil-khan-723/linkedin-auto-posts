# LinkedIn Auto Posts

Fully autonomous LinkedIn post scheduler. Runs 3x/week (Mon/Wed/Fri, 10am IST) with zero manual involvement. Posts niche DevOps content from a learning perspective, sourced from GitHub repos.

---

## How It Works

```
Schedule trigger (Mon/Wed/Fri 10am IST)
        │
        ▼
  GitHub Scraper
  Fetches repos, READMEs, commits from adil-khan-723
        │
        ▼
  Topic Picker
  Picks unused niche angle — GitHub repos first, self-generated fallback
        │
        ▼
  Post Generator (Claude Code)
  Writes post: learning POV, 5-7yr DevOps practitioner voice, prose only
        │
        ▼
  Humanizer Pass
  Strips AI patterns: em dashes, filler phrases, passive voice clusters
        │
        ▼
  Quality Gate
  Rejects if generic, tutorial-like, CTO-sounding, or too short/long
  Retries up to 3x — skips day after 3 failures
        │
        ▼
  LinkedIn Poster
  POSTs to LinkedIn Share API v2, logs result
```

---

## Post Voice & Tone

- **Who:** 5-7 year DevOps practitioner who uses tools daily — not someone who built them
- **NOT:** CTO, architect, platform engineer explaining system internals
- **Style:** Prose only, 150-250 words, first person, ends with open question
- **Angle:** "here's what I ran into" — not "here's how to do X"

---

## File Structure

```
├── github_scraper.py        # Fetches repo data from GitHub API
├── topic_picker.py          # Selects unused topic, writes selected_topic.json
├── linkedin_poster.py       # Posts to LinkedIn API v2, updates state files
├── prompts/
│   ├── agent_instructions.md  # Full pipeline Claude Code follows each run
│   ├── post_generator.md      # Rules for writing the post
│   ├── humanizer_rules.md     # AI pattern removal rules
│   └── quality_criteria.md   # Pass/fail criteria
├── data/
│   ├── posted_topics.json     # Tracks used topics + post IDs (persistent)
│   ├── run_log.json           # Per-run history: date, topic, success/failure
│   ├── scraped_data.json      # Latest GitHub scrape output (ephemeral)
│   └── selected_topic.json    # Current run's picked topic (ephemeral)
├── tests/
│   ├── test_github_scraper.py
│   ├── test_topic_picker.py
│   └── test_linkedin_poster.py
├── .env                     # LinkedIn credentials
└── requirements.txt
```

---

## Schedule

| Field | Value |
|-------|-------|
| Days | Monday, Wednesday, Friday |
| Time | 10:00am IST (4:30am UTC) |
| Routine ID | `trig_01CdA8YWa1EAGbHtxVAi5KNx` |
| Manage | https://claude.ai/code/routines/trig_01CdA8YWa1EAGbHtxVAi5KNx |

Runs fully in Anthropic's cloud. **Mac does not need to be on.**

---

## Topic Sources

Posts pull from these repos (GitHub first, self-generated fallback if all used):

- `cicd-ai-copilot` — AI CI/CD failure analysis, Jenkins/GHA
- `iacguard` — Terraform blast radius, pre-apply risk
- `k8s-observability-stack` — Prometheus, ServiceMonitor, PromQL, Grafana
- `kubernetes-sample-voting-app-project-tls` — K8s networking, ingress, TLS
- `K8s-RBAC` — RBAC, ServiceAccounts, RoleBindings
- `EKS-Terraform-Provisioning` — EKS + Terraform, IAM, VPC
- `slim-vs-alpine` — Docker image comparison, glibc vs musl
- `terraform_project2_refactored` — ALB, S3 remote state, DynamoDB locking
- `terraform-project2-moudlarized` — Terraform module design
- `microservices` — Docker Compose, healthchecks, internal DNS

Self-generated fallback pool covers: K8s readiness/liveness probes, Terraform DynamoDB locking, Docker layer caching, resource requests vs limits, Jenkins shared libraries, Alpine runtime failures, Prometheus intervals, and more.

---

## Maintenance

### LinkedIn Token (every ~53 days)

The token expires after 60 days. System logs a warning 7 days before expiry in `data/run_log.json`.

**To renew:**
1. Go to [LinkedIn Developer Portal](https://developer.linkedin.com)
2. Generate new access token with `w_member_social` scope
3. Update `.env` in this repo:
   ```
   LINKEDIN_ACCESS_TOKEN=<new token>
   ```
4. Commit and push

### Checking Run Status

After any scheduled run, check `data/run_log.json` in this repo:

```json
{
  "runs": [
    {
      "date": "2026-05-05T04:31:22",
      "topic": "iacguard: Terraform blast radius analyzer",
      "source": "github",
      "success": true,
      "post_id": "urn:li:share:...",
      "error": null
    }
  ]
}
```

`success: false` with an error means something failed — check the error field.

### Pausing / Stopping

Visit https://claude.ai/code/routines/trig_01CdA8YWa1EAGbHtxVAi5KNx and toggle the routine off.

---

## Local Development

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run tests
pytest tests/ -v

# Dry run (no LinkedIn post)
python github_scraper.py
python topic_picker.py
cat data/selected_topic.json
```

---

## Dependencies

- `requests` — GitHub API + LinkedIn API HTTP calls
- `python-dotenv` — Load `.env` credentials
- `pytest` — Test suite (13 tests)
