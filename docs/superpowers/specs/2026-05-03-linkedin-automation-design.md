# LinkedIn Automation System — Design Spec

Date: 2026-05-03

## Goal

Fully autonomous LinkedIn posting system. Posts 3x/week (Mon/Wed/Fri) with zero manual involvement after one-time setup. Content sourced from GitHub profile `adil-khan-723`, written from a DevOps learning perspective, humanized to remove AI patterns, self-reviewed before posting.

## Voice & Tone

- **Target level:** 5-7 year DevOps practitioner who uses tools deeply from daily experience
- **NOT:** CTO, platform engineer, tool builder, architect
- Sounds like: "I use this tool constantly and hit this edge case"
- Does NOT sound like: "I designed this system" or "here's how this works under the hood"
- Prose only — no bullet lists, no headers, no numbered steps
- 150-250 words per post
- Ends with open question or "still figuring out X" — never a lesson summary
- Learning POV: shares what he's discovering, not teaching others

## Pipeline

```
Schedule trigger (Mon / Wed / Fri, 10am)
        │
        ▼
  GitHub Scraper
  - fetch all repos via GitHub API (adil-khan-723)
  - pull README + recent commits per repo
        │
        ▼
  Topic Picker
  - extract niche angles from repo content
  - check posted_topics.json → skip already-used topics
  - select one deep, specific angle
        │
        ▼
  Post Generator (Claude Code subscription)
  - prompt enforces: learning POV, practitioner depth, no fluff
  - produces raw draft
        │
        ▼
  Humanizer Pass
  - strips AI patterns: inflated language, em dashes, rule-of-three,
    passive voice, filler phrases, "In conclusion" / "Key takeaway"
        │
        ▼
  Quality Gate (self-review)
  - rejects if fails criteria → retry (max 3)
  - after 3 failures: log + skip day
        │
        ▼
  LinkedIn Poster
  - POST to LinkedIn Share API v2 (/ugcPosts)
  - logs topic + post URL to posted_topics.json
```

## Components

| File | Responsibility |
|------|---------------|
| `main.py` | Orchestrator — calls each module in order |
| `github_scraper.py` | GitHub API → repos, READMEs, commit messages |
| `topic_picker.py` | Extract niche angles, deduplicate via posted_topics.json |
| `post_generator.py` | Build prompt + instructions — Claude Code agent generates the draft |
| `humanizer.py` | Humanizer rules applied by Claude Code agent inline |
| `quality_gate.py` | Quality criteria — Claude Code agent scores + rejects/passes |
| `linkedin_poster.py` | LinkedIn Share API v2 POST + log result |
| `posted_topics.json` | State — used topics + post URLs |
| `run_log.json` | Per-run logs: date, topic, result/error |
| `.env` | LinkedIn credentials (never committed) |
| `requirements.txt` | requests, python-dotenv |

## Quality Gate Rules

Reject post if any of these match:
- Contains "In conclusion", "Key takeaway", "In this post", "This allows you to"
- Reads like a tutorial (step 1 / step 2 pattern detected)
- Sounds like documentation or architecture overview
- Expertise level sounds like architect/CTO (flagged by secondary prompt check)
- Under 100 words or over 300 words

Max 3 retries per run. On 3rd failure: log to `run_log.json`, skip that day.

## Topic Fallback

If no suitable topic found in GitHub repos (all used, or none match depth/niche requirements), Claude Code generates topic autonomously. Fallback pool: real DevOps concepts within user's stack (Terraform, K8s, Docker, Jenkins, AWS, observability) — practitioner depth, learning angle, never surface-level. Fallback logged in `run_log.json` as `source: self-generated`.

## Topic Sourcing

Key repos to mine:
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

## LinkedIn API

- Endpoint: `POST https://api.linkedin.com/v2/ugcPosts`
- Auth: OAuth 2.0 access token (`w_member_social` scope)
- Credentials stored in `.env` only
- Token expiry: system logs warning 7 days before 60-day expiry

## Runtime Architecture

Python scripts handle data I/O only (GitHub scraping, LinkedIn posting, state files). Claude Code IS the runtime agent — it reads scraper output, generates post content, applies humanizer rules, and runs quality gate. No Anthropic API key required in code — Claude Code subscription covers all generation.

## Schedule

- Trigger: Mon / Wed / Fri at 10am (local timezone)
- Configured via Claude Code `/schedule` skill
- Claude Code agent runs the full pipeline (no API key in scripts)

## Folder Structure

```
/Users/oggy/Posts/
├── main.py
├── github_scraper.py
├── topic_picker.py
├── post_generator.py
├── humanizer.py
├── quality_gate.py
├── linkedin_poster.py
├── posted_topics.json
├── run_log.json
├── .env
├── .gitignore               # excludes .env
└── requirements.txt
```

## One-Time Setup (user action required)

1. LinkedIn Developer Portal → create app → get `client_id` + `client_secret`
2. Generate access token with `w_member_social` scope
3. Paste into `.env`
4. Run Claude Code `/schedule` to register cron

After setup: zero involvement needed.
