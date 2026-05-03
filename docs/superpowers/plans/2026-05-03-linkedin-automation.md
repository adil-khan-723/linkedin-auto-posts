# LinkedIn Automation System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a fully autonomous LinkedIn post scheduler that scrapes GitHub repos, generates niche DevOps posts from a learning perspective, humanizes them, self-reviews, and posts 3x/week via Claude Code subscription.

**Architecture:** Python scripts handle all data I/O (GitHub scraping, LinkedIn posting, state management). Claude Code IS the content generation runtime — it reads scraper output, writes posts, applies humanizer rules, and runs quality gate checks. No Anthropic API key needed in code — Claude Code subscription covers all generation.

**Tech Stack:** Python 3.11+, requests, python-dotenv, pytest, LinkedIn Share API v2, GitHub REST API v3, Claude Code `/schedule` skill.

---

## File Map

| File | Responsibility |
|------|---------------|
| `github_scraper.py` | GitHub API → `data/scraped_data.json` |
| `topic_picker.py` | Select unused topic → `data/selected_topic.json` |
| `linkedin_poster.py` | Read approved post → POST LinkedIn API → update state |
| `prompts/post_generator.md` | Claude's rules for writing the post |
| `prompts/humanizer_rules.md` | Patterns to strip from draft |
| `prompts/quality_criteria.md` | Pass/fail criteria for self-review |
| `prompts/agent_instructions.md` | Full pipeline prompt used by `/schedule` |
| `data/posted_topics.json` | Persistent: used topics + post IDs |
| `data/run_log.json` | Persistent: per-run history |
| `data/scraped_data.json` | Ephemeral: latest GitHub scrape |
| `data/selected_topic.json` | Ephemeral: picked topic for current run |
| `data/.linkedin_person_id` | Cached LinkedIn person ID |
| `tests/test_github_scraper.py` | Scraper unit tests |
| `tests/test_topic_picker.py` | Picker unit tests |
| `tests/test_linkedin_poster.py` | Poster unit tests |
| `.env` | LinkedIn credentials (never committed) |
| `requirements.txt` | Python deps |
| `.gitignore` | Excludes .env, data/.linkedin_person_id |

---

## Task 1: Project Setup

**Files:**
- Create: `requirements.txt`
- Create: `.gitignore`
- Create: `.env`
- Create: `data/posted_topics.json`
- Create: `data/run_log.json`
- Create: `data/scraped_data.json`
- Create: `data/selected_topic.json`

- [ ] **Step 1: Create requirements.txt**

```
requests==2.32.3
python-dotenv==1.0.1
pytest==8.3.4
```

- [ ] **Step 2: Create .gitignore**

```
.env
data/.linkedin_person_id
__pycache__/
*.pyc
.pytest_cache/
```

- [ ] **Step 3: Create .env with LinkedIn credentials**

```
LINKEDIN_CLIENT_ID=77czdpan5sfyfu
LINKEDIN_CLIENT_SECRET=WPL_AP1.J9x3YpA2PNN8LDqh.YwyT5g==
LINKEDIN_ACCESS_TOKEN=AQWfvbX_kXvPswQX4d8t6K5wftV-FnKuERyC78fe21QhJe6RIMKah6EAFsgGmvFcLbDDdpNac3OfDwXrZsTB8pUg6_kr7vufCl96jJXiNSu7cUhBholniO8RgrqLFBAX1Dw_AE6Ss4-QcoHYDmoLqfGiIHPvOcWnJyZs7ovLZ1DLYZgpQ9rudvvNPJy7fDtpHSFMt0FbKLZE4zVo_Y_VowP3MydxZQeovf8EWaMnU9c496tSFnfCFQQGjMV6ByhsGSE3Ft3FdOeUDDSlD4jaMPTDbnA1Mqm5s3k9v21qNEgKh_eYMZk3uUVP_bHFrmP6Kw-pCD1qG7WIanBHhiyFWOZhJdeurg
```

- [ ] **Step 4: Create empty state files**

`data/posted_topics.json`:
```json
{"posted": []}
```

`data/run_log.json`:
```json
{"runs": []}
```

`data/scraped_data.json`:
```json
{"repos": [], "scraped_at": null}
```

`data/selected_topic.json`:
```json
{}
```

- [ ] **Step 5: Install dependencies**

Run: `pip install -r requirements.txt`
Expected: all 3 packages install without error.

- [ ] **Step 6: Commit**

```bash
git init
git add requirements.txt .gitignore
git commit -m "chore: project setup"
```

---

## Task 2: GitHub Scraper

**Files:**
- Create: `github_scraper.py`
- Create: `tests/test_github_scraper.py`

- [ ] **Step 1: Write failing tests**

`tests/test_github_scraper.py`:
```python
import json
import base64
import pytest
from unittest.mock import patch, MagicMock
import github_scraper


MOCK_REPO = {
    "name": "iacguard",
    "description": "Terraform pre-apply risk analyzer",
    "language": "Python",
    "updated_at": "2026-03-23T07:30:27Z"
}
MOCK_README = {
    "content": base64.b64encode(b"# IACGuard\nAnalyze Terraform blast radius").decode()
}
MOCK_COMMITS = [
    {"commit": {"message": "feat: initial release\n\nMore details"}},
    {"commit": {"message": "fix: update pyproject.toml"}}
]


def test_fetch_repo_data_returns_structured_data():
    with patch("github_scraper.requests.get") as mock_get:
        mock_get.side_effect = [
            MagicMock(status_code=200, json=lambda: MOCK_REPO),
            MagicMock(status_code=200, json=lambda: MOCK_README),
            MagicMock(status_code=200, json=lambda: MOCK_COMMITS),
        ]
        result = github_scraper.fetch_repo_data("iacguard")

    assert result["name"] == "iacguard"
    assert result["description"] == "Terraform pre-apply risk analyzer"
    assert "IACGuard" in result["readme"]
    assert result["recent_commits"] == ["feat: initial release", "fix: update pyproject.toml"]


def test_fetch_repo_data_returns_none_on_404():
    with patch("github_scraper.requests.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=404)
        result = github_scraper.fetch_repo_data("nonexistent-repo")
    assert result is None


def test_fetch_repo_data_caps_readme_at_3000_chars():
    long_readme = {"content": base64.b64encode(("x" * 5000).encode()).decode()}
    with patch("github_scraper.requests.get") as mock_get:
        mock_get.side_effect = [
            MagicMock(status_code=200, json=lambda: MOCK_REPO),
            MagicMock(status_code=200, json=lambda: long_readme),
            MagicMock(status_code=200, json=lambda: []),
        ]
        result = github_scraper.fetch_repo_data("iacguard")
    assert len(result["readme"]) <= 3000


def test_scrape_writes_output_file(tmp_path, monkeypatch):
    monkeypatch.setattr(github_scraper, "OUTPUT_FILE", str(tmp_path / "scraped_data.json"))
    monkeypatch.setattr(github_scraper, "DEVOPS_REPOS", ["iacguard"])

    with patch("github_scraper.requests.get") as mock_get:
        mock_get.side_effect = [
            MagicMock(status_code=200, json=lambda: MOCK_REPO),
            MagicMock(status_code=200, json=lambda: MOCK_README),
            MagicMock(status_code=200, json=lambda: MOCK_COMMITS),
        ]
        github_scraper.scrape()

    output = json.loads((tmp_path / "scraped_data.json").read_text())
    assert "repos" in output
    assert len(output["repos"]) == 1
    assert "scraped_at" in output
```

- [ ] **Step 2: Run tests — verify they fail**

Run: `pytest tests/test_github_scraper.py -v`
Expected: `ModuleNotFoundError: No module named 'github_scraper'`

- [ ] **Step 3: Implement github_scraper.py**

```python
import os
import json
import base64
import requests
from datetime import datetime

GITHUB_USERNAME = "adil-khan-723"
GITHUB_API = "https://api.github.com"
OUTPUT_FILE = "data/scraped_data.json"

DEVOPS_REPOS = [
    "cicd-ai-copilot",
    "iacguard",
    "k8s-observability-stack",
    "kubernetes-sample-voting-app-project-tls",
    "K8s-RBAC",
    "EKS-Terraform-Provisioning",
    "slim-vs-alpine",
    "terraform_project2_refactored",
    "terraform-project2-moudlarized",
    "microservices",
    "terraform-aws-infra",
    "terraform-docker-ci-cd-project3",
    "kubernetes-sample-voting-app-project1",
]


def fetch_repo_data(repo_name):
    headers = {"Accept": "application/vnd.github.v3+json"}

    repo_resp = requests.get(
        f"{GITHUB_API}/repos/{GITHUB_USERNAME}/{repo_name}", headers=headers
    )
    if repo_resp.status_code != 200:
        return None
    repo = repo_resp.json()

    readme = ""
    readme_resp = requests.get(
        f"{GITHUB_API}/repos/{GITHUB_USERNAME}/{repo_name}/readme", headers=headers
    )
    if readme_resp.status_code == 200:
        readme = base64.b64decode(readme_resp.json()["content"]).decode(
            "utf-8", errors="ignore"
        )[:3000]

    commits = []
    commits_resp = requests.get(
        f"{GITHUB_API}/repos/{GITHUB_USERNAME}/{repo_name}/commits",
        headers=headers,
        params={"per_page": 10},
    )
    if commits_resp.status_code == 200:
        commits = [
            c["commit"]["message"].split("\n")[0] for c in commits_resp.json()
        ]

    return {
        "name": repo_name,
        "description": repo.get("description", ""),
        "language": repo.get("language", ""),
        "readme": readme,
        "recent_commits": commits,
        "updated_at": repo.get("updated_at", ""),
    }


def scrape():
    repos = []
    for repo_name in DEVOPS_REPOS:
        data = fetch_repo_data(repo_name)
        if data:
            repos.append(data)

    output = {"repos": repos, "scraped_at": datetime.utcnow().isoformat()}

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Scraped {len(repos)} repos → {OUTPUT_FILE}")


if __name__ == "__main__":
    scrape()
```

- [ ] **Step 4: Run tests — verify they pass**

Run: `pytest tests/test_github_scraper.py -v`
Expected: 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add github_scraper.py tests/test_github_scraper.py
git commit -m "feat: add GitHub scraper with tests"
```

---

## Task 3: Topic Picker

**Files:**
- Create: `topic_picker.py`
- Create: `tests/test_topic_picker.py`

- [ ] **Step 1: Write failing tests**

`tests/test_topic_picker.py`:
```python
import json
import pytest
import topic_picker

SAMPLE_SCRAPED = {
    "repos": [
        {
            "name": "iacguard",
            "description": "Terraform blast radius analyzer",
            "language": "Python",
            "readme": "# IACGuard\nAnalyze blast radius before apply",
            "recent_commits": ["feat: initial release"],
            "updated_at": "2026-03-23",
        }
    ]
}


def test_pick_topic_selects_github_topic_when_available(tmp_path, monkeypatch):
    scraped = tmp_path / "scraped.json"
    posted = tmp_path / "posted.json"
    output = tmp_path / "selected.json"

    scraped.write_text(json.dumps(SAMPLE_SCRAPED))
    posted.write_text(json.dumps({"posted": []}))

    monkeypatch.setattr(topic_picker, "SCRAPED_FILE", str(scraped))
    monkeypatch.setattr(topic_picker, "POSTED_FILE", str(posted))
    monkeypatch.setattr(topic_picker, "OUTPUT_FILE", str(output))

    topic_picker.pick_topic()

    result = json.loads(output.read_text())
    assert result["source"] == "github"
    assert "iacguard" in result["topic"]


def test_pick_topic_falls_back_to_self_generated_when_all_used(tmp_path, monkeypatch):
    scraped = tmp_path / "scraped.json"
    posted = tmp_path / "posted.json"
    output = tmp_path / "selected.json"

    scraped.write_text(json.dumps(SAMPLE_SCRAPED))
    used_topic = "iacguard: Terraform blast radius analyzer"
    posted.write_text(json.dumps({"posted": [{"topic": used_topic}]}))

    monkeypatch.setattr(topic_picker, "SCRAPED_FILE", str(scraped))
    monkeypatch.setattr(topic_picker, "POSTED_FILE", str(posted))
    monkeypatch.setattr(topic_picker, "OUTPUT_FILE", str(output))

    topic_picker.pick_topic()

    result = json.loads(output.read_text())
    assert result["source"] == "self-generated"


def test_pick_topic_skips_used_topics(tmp_path, monkeypatch):
    scraped = tmp_path / "scraped.json"
    posted = tmp_path / "posted.json"
    output = tmp_path / "selected.json"

    scraped.write_text(json.dumps(SAMPLE_SCRAPED))
    first_self_gen = topic_picker.SELF_GENERATED_TOPICS[0]["topic"]
    github_topic = "iacguard: Terraform blast radius analyzer"
    posted.write_text(json.dumps({
        "posted": [
            {"topic": github_topic},
            {"topic": first_self_gen},
        ]
    }))

    monkeypatch.setattr(topic_picker, "SCRAPED_FILE", str(scraped))
    monkeypatch.setattr(topic_picker, "POSTED_FILE", str(posted))
    monkeypatch.setattr(topic_picker, "OUTPUT_FILE", str(output))

    topic_picker.pick_topic()

    result = json.loads(output.read_text())
    assert result["topic"] != github_topic
    assert result["topic"] != first_self_gen


def test_pick_topic_output_has_required_fields(tmp_path, monkeypatch):
    scraped = tmp_path / "scraped.json"
    posted = tmp_path / "posted.json"
    output = tmp_path / "selected.json"

    scraped.write_text(json.dumps(SAMPLE_SCRAPED))
    posted.write_text(json.dumps({"posted": []}))

    monkeypatch.setattr(topic_picker, "SCRAPED_FILE", str(scraped))
    monkeypatch.setattr(topic_picker, "POSTED_FILE", str(posted))
    monkeypatch.setattr(topic_picker, "OUTPUT_FILE", str(output))

    topic_picker.pick_topic()

    result = json.loads(output.read_text())
    for field in ["topic", "angle", "source", "selected_at"]:
        assert field in result, f"Missing field: {field}"
```

- [ ] **Step 2: Run tests — verify they fail**

Run: `pytest tests/test_topic_picker.py -v`
Expected: `ModuleNotFoundError: No module named 'topic_picker'`

- [ ] **Step 3: Implement topic_picker.py**

```python
import json
import os
from datetime import datetime

SCRAPED_FILE = "data/scraped_data.json"
POSTED_FILE = "data/posted_topics.json"
OUTPUT_FILE = "data/selected_topic.json"

SELF_GENERATED_TOPICS = [
    {
        "topic": "Why Kubernetes readiness and liveness probes are not interchangeable",
        "angle": "liveness probe killed a slow-start pod and I had to trace why",
        "repo": None,
    },
    {
        "topic": "Terraform state lock stuck in DynamoDB — how to recover without panic",
        "angle": "manually deleting stale lock entry after a failed apply",
        "repo": None,
    },
    {
        "topic": "Docker layer caching breaks when COPY order is wrong",
        "angle": "was rebuilding entire image every time due to wrong COPY placement",
        "repo": None,
    },
    {
        "topic": "Kubernetes resource requests vs limits — not the same thing",
        "angle": "node OOM killed my pod and I didn't understand why until I looked at limits",
        "repo": None,
    },
    {
        "topic": "Jenkins shared libraries — why they exist and when they click",
        "angle": "copy-pasted the same Jenkinsfile 8 times before finally getting it",
        "repo": None,
    },
    {
        "topic": "Alpine images that work locally but break in production",
        "angle": "musl vs glibc at runtime — not obvious until it crashes",
        "repo": None,
    },
    {
        "topic": "Prometheus scrape interval vs evaluation interval",
        "angle": "alert was firing late and I couldn't figure out why for hours",
        "repo": None,
    },
    {
        "topic": "Terraform depends_on when implicit dependencies aren't enough",
        "angle": "race condition on resource creation that only happened occasionally",
        "repo": None,
    },
    {
        "topic": "Kubernetes terminationGracePeriodSeconds alone isn't enough for zero-downtime deploys",
        "angle": "still getting 502s on rolling deploy until I added preStop sleep",
        "repo": None,
    },
    {
        "topic": "EKS node groups vs managed node groups — what actually changes",
        "angle": "assumed they were the same until I hit a patching issue",
        "repo": None,
    },
]


def load_json(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def extract_repo_topics(repos):
    return [
        {
            "topic": f"{r['name']}: {r['description'] or r['name']}",
            "angle": f"commits: {', '.join(r['recent_commits'][:3])}",
            "repo": r["name"],
            "source": "github",
        }
        for r in repos
        if r.get("description")
    ]


def pick_topic():
    scraped = load_json(SCRAPED_FILE, {"repos": []})
    posted = load_json(POSTED_FILE, {"posted": []})

    used = {p["topic"] for p in posted.get("posted", [])}

    candidates = extract_repo_topics(scraped["repos"])
    unused_github = [t for t in candidates if t["topic"] not in used]

    if unused_github:
        selected = {**unused_github[0], "source": "github"}
    else:
        unused_self = [t for t in SELF_GENERATED_TOPICS if t["topic"] not in used]
        if not unused_self:
            unused_self = SELF_GENERATED_TOPICS
        selected = {**unused_self[0], "source": "self-generated"}

    result = {
        "topic": selected["topic"],
        "angle": selected["angle"],
        "repo": selected.get("repo"),
        "source": selected["source"],
        "selected_at": datetime.utcnow().isoformat(),
    }

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(result, f, indent=2)

    print(f"Selected: {result['topic']} (source: {result['source']})")


if __name__ == "__main__":
    pick_topic()
```

- [ ] **Step 4: Run tests — verify they pass**

Run: `pytest tests/test_topic_picker.py -v`
Expected: 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add topic_picker.py tests/test_topic_picker.py
git commit -m "feat: add topic picker with fallback to self-generated topics"
```

---

## Task 4: LinkedIn Poster

**Files:**
- Create: `linkedin_poster.py`
- Create: `tests/test_linkedin_poster.py`

- [ ] **Step 1: Write failing tests**

`tests/test_linkedin_poster.py`:
```python
import json
import pytest
from unittest.mock import patch, MagicMock
import linkedin_poster


def test_get_person_id_fetches_from_api(tmp_path, monkeypatch):
    monkeypatch.setattr(linkedin_poster, "PERSON_ID_FILE", str(tmp_path / ".pid"))

    with patch("linkedin_poster.requests.get") as mock_get:
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"id": "abc123"},
            raise_for_status=lambda: None,
        )
        result = linkedin_poster.get_person_id("fake_token")

    assert result == "abc123"


def test_get_person_id_uses_cache(tmp_path, monkeypatch):
    cache = tmp_path / ".pid"
    cache.write_text("cached_456")
    monkeypatch.setattr(linkedin_poster, "PERSON_ID_FILE", str(cache))

    with patch("linkedin_poster.requests.get") as mock_get:
        result = linkedin_poster.get_person_id("fake_token")

    assert result == "cached_456"
    mock_get.assert_not_called()


def test_post_to_linkedin_sends_correct_payload():
    mock_resp = MagicMock(
        headers={"x-restli-id": "post_789"},
        raise_for_status=lambda: None,
    )
    with patch("linkedin_poster.requests.post", return_value=mock_resp) as mock_post:
        post_id = linkedin_poster.post_to_linkedin("Test post text", "token", "person123")

    assert post_id == "post_789"
    payload = mock_post.call_args[1]["json"]
    assert payload["author"] == "urn:li:person:person123"
    assert (
        payload["specificContent"]["com.linkedin.ugc.ShareContent"]["shareCommentary"]["text"]
        == "Test post text"
    )
    assert payload["lifecycleState"] == "PUBLISHED"
    assert payload["visibility"]["com.linkedin.ugc.MemberNetworkVisibility"] == "PUBLIC"


def test_log_and_update_on_success(tmp_path, monkeypatch):
    monkeypatch.setattr(linkedin_poster, "POSTED_FILE", str(tmp_path / "posted.json"))
    monkeypatch.setattr(linkedin_poster, "RUN_LOG_FILE", str(tmp_path / "run_log.json"))

    linkedin_poster.log_and_update(
        "post text",
        "post_id_123",
        {"topic": "test topic", "source": "github", "repo": "iacguard"},
        success=True,
    )

    posted = json.loads((tmp_path / "posted.json").read_text())
    assert posted["posted"][0]["topic"] == "test topic"
    assert posted["posted"][0]["post_id"] == "post_id_123"

    run_log = json.loads((tmp_path / "run_log.json").read_text())
    assert run_log["runs"][0]["success"] is True
    assert run_log["runs"][0]["error"] is None


def test_log_and_update_on_failure(tmp_path, monkeypatch):
    monkeypatch.setattr(linkedin_poster, "POSTED_FILE", str(tmp_path / "posted.json"))
    monkeypatch.setattr(linkedin_poster, "RUN_LOG_FILE", str(tmp_path / "run_log.json"))

    linkedin_poster.log_and_update(
        "post text",
        None,
        {"topic": "test topic", "source": "github", "repo": "iacguard"},
        success=False,
        error="401 Unauthorized",
    )

    posted = json.loads((tmp_path / "posted.json").read_text())
    assert posted["posted"] == []

    run_log = json.loads((tmp_path / "run_log.json").read_text())
    assert run_log["runs"][0]["success"] is False
    assert run_log["runs"][0]["error"] == "401 Unauthorized"
```

- [ ] **Step 2: Run tests — verify they fail**

Run: `pytest tests/test_linkedin_poster.py -v`
Expected: `ModuleNotFoundError: No module named 'linkedin_poster'`

- [ ] **Step 3: Implement linkedin_poster.py**

```python
import os
import sys
import json
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

LINKEDIN_API = "https://api.linkedin.com/v2"
POSTED_FILE = "data/posted_topics.json"
RUN_LOG_FILE = "data/run_log.json"
SELECTED_TOPIC_FILE = "data/selected_topic.json"
PERSON_ID_FILE = "data/.linkedin_person_id"


def get_access_token():
    token = os.getenv("LINKEDIN_ACCESS_TOKEN")
    if not token:
        raise ValueError("LINKEDIN_ACCESS_TOKEN not set in .env")
    return token


def get_person_id(token):
    if os.path.exists(PERSON_ID_FILE):
        with open(PERSON_ID_FILE) as f:
            return f.read().strip()

    resp = requests.get(
        f"{LINKEDIN_API}/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    resp.raise_for_status()
    person_id = resp.json()["id"]

    os.makedirs(os.path.dirname(PERSON_ID_FILE), exist_ok=True)
    with open(PERSON_ID_FILE, "w") as f:
        f.write(person_id)

    return person_id


def post_to_linkedin(text, token, person_id):
    payload = {
        "author": f"urn:li:person:{person_id}",
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": text},
                "shareMediaCategory": "NONE",
            }
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
        },
    }

    resp = requests.post(
        f"{LINKEDIN_API}/ugcPosts",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
        },
        json=payload,
    )
    resp.raise_for_status()
    return resp.headers.get("x-restli-id", "unknown")


def load_json(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def log_and_update(post_text, post_id, topic_data, success, error=None):
    posted = load_json(POSTED_FILE, {"posted": []})
    if success:
        posted["posted"].append({
            "topic": topic_data.get("topic", ""),
            "source": topic_data.get("source", ""),
            "repo": topic_data.get("repo"),
            "post_id": post_id,
            "posted_at": datetime.utcnow().isoformat(),
        })
        save_json(POSTED_FILE, posted)

    run_log = load_json(RUN_LOG_FILE, {"runs": []})
    run_log["runs"].append({
        "date": datetime.utcnow().isoformat(),
        "topic": topic_data.get("topic", ""),
        "source": topic_data.get("source", ""),
        "success": success,
        "post_id": post_id if success else None,
        "error": error,
    })
    save_json(RUN_LOG_FILE, run_log)


def main():
    if len(sys.argv) > 1:
        post_text = " ".join(sys.argv[1:])
    else:
        post_text = sys.stdin.read().strip()

    if not post_text:
        print("ERROR: no post text provided")
        sys.exit(1)

    topic_data = load_json(SELECTED_TOPIC_FILE, {})

    try:
        token = get_access_token()
        person_id = get_person_id(token)
        post_id = post_to_linkedin(post_text, token, person_id)
        log_and_update(post_text, post_id, topic_data, success=True)
        print(f"Posted successfully. ID: {post_id}")
    except Exception as e:
        log_and_update(post_text, None, topic_data, success=False, error=str(e))
        print(f"ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests — verify they pass**

Run: `pytest tests/test_linkedin_poster.py -v`
Expected: 5 tests PASS

- [ ] **Step 5: Run full test suite**

Run: `pytest tests/ -v`
Expected: 13 tests PASS, 0 failures

- [ ] **Step 6: Commit**

```bash
git add linkedin_poster.py tests/test_linkedin_poster.py
git commit -m "feat: add LinkedIn poster with caching and state logging"
```

---

## Task 5: Prompt Files

**Files:**
- Create: `prompts/post_generator.md`
- Create: `prompts/humanizer_rules.md`
- Create: `prompts/quality_criteria.md`
- Create: `prompts/agent_instructions.md`

- [ ] **Step 1: Create prompts/post_generator.md**

```markdown
# Post Generator Rules

Write a LinkedIn post as Adil — a DevOps engineer with 5-7 years of hands-on experience who shares what he's currently figuring out.

## Who Adil is
- Uses tools daily — does NOT build or design them
- Knows tools inside-out from real operational experience
- Curious, occasionally frustrated, sometimes surprised by edge cases
- Writes from experience: "here's what I ran into" not "here's how to do X"
- Would never say "as a DevOps engineer" or explain what DevOps is

## Topic Input
Read data/selected_topic.json. Use the `topic` and `angle` fields as the starting point.

## What to write
- One specific incident, discovery, or realization — not a general overview
- The moment something clicked, or didn't click yet
- Concrete: name the actual tool, flag, config, or behavior
- Show the confusion first, then what was learned (if anything)
- End with open question or "still figuring out X" — never a tidy lesson

## Format Rules
- Prose only — no bullet points, no headers, no numbered steps
- 150-250 words
- First person throughout
- No hashtags
- Do NOT start with "Today I learned" or "I recently discovered"

Output ONLY the post text. Nothing else.
```

- [ ] **Step 2: Create prompts/humanizer_rules.md**

```markdown
# Humanizer Rules

Review the draft post and fix any of the following patterns:

1. **Em dashes** (—) → replace with comma or restructure sentence
2. **"Not only X but also Y"** → rewrite as simpler sentence
3. **Closing phrases** ("In conclusion", "To summarize", "Key takeaway", "In this post") → delete entire sentence
4. **AI vocabulary** ("Delve", "Navigate", "Leverage", "Utilize", "Robust", "Seamless", "Cutting-edge") → replace with plain word
5. **Rule of three** (exactly 3 items listed for rhetorical effect) → use 2 or 4 instead
6. **Passive voice clusters** (more than 2 passive sentences in a row) → rewrite to active
7. **Filler openers** ("It's worth noting that", "Interestingly,", "It's important to", "One thing to note") → delete
8. **Hashtags** → remove all
9. **"This allows you to..."** → rewrite with active subject

Apply all fixes. Output ONLY the revised post text. Nothing else.
```

- [ ] **Step 3: Create prompts/quality_criteria.md**

```markdown
# Quality Gate Criteria

Evaluate the post against these rules. One failure = REJECT.

## REJECT if any of these are true:

1. Contains "In conclusion", "Key takeaway", "In this post", "This allows you to", "I hope this helps"
2. Contains numbered steps (1. ... 2. ...) or bullet points (- or •)
3. Reads like a tutorial or how-to guide
4. Sounds like a CTO, architect, or someone explaining how a system was designed internally
5. Word count under 100 or over 300
6. Contains hashtags (#anything)
7. Ends with a lesson summary or moral
8. Sounds generic — could have been written about any company, any team, any project
9. No specific technical detail (tool name, config key, flag, behavior, error)

## Response format

If REJECTED: respond with exactly this format (one line):
REJECT: [specific reason]

If PASSED: respond with exactly:
PASS
```

- [ ] **Step 4: Create prompts/agent_instructions.md**

```markdown
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
```

- [ ] **Step 5: Commit**

```bash
git add prompts/
git commit -m "feat: add agent prompt files for generation, humanizer, quality gate, and pipeline"
```

---

## Task 6: Register Schedule

**No files created — configure Claude Code `/schedule`.**

- [ ] **Step 1: Verify all tests still pass**

Run: `pytest tests/ -v`
Expected: 13 tests PASS

- [ ] **Step 2: Do a dry run of Python scripts manually**

```bash
python github_scraper.py
```
Expected: "Scraped N repos → data/scraped_data.json"

```bash
python topic_picker.py
```
Expected: "Selected: [topic name] (source: github)"

- [ ] **Step 3: Register schedule via Claude Code**

In Claude Code, run:
```
/schedule
```

When prompted:
- **Task prompt:** "Follow the instructions in /Users/oggy/Posts/prompts/agent_instructions.md exactly."
- **Working directory:** `/Users/oggy/Posts`
- **Schedule:** `0 10 * * 1,3,5` (Mon/Wed/Fri at 10am)

- [ ] **Step 4: Add token expiry check to agent_instructions.md**

Append this block to `prompts/agent_instructions.md` after Step 8:

```markdown
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
```

- [ ] **Step 5: Verify schedule registered**

Run in Claude Code: `/schedule list` (or equivalent)
Expected: see the LinkedIn pipeline task listed with next run time.

- [ ] **Step 6: Final commit**

```bash
git add data/posted_topics.json data/run_log.json data/scraped_data.json data/selected_topic.json prompts/agent_instructions.md
git commit -m "chore: add initial state files and token expiry check"
```

---

## Post-Setup Checklist

- [ ] `.env` exists with valid `LINKEDIN_ACCESS_TOKEN`
- [ ] `data/posted_topics.json` contains `{"posted": []}`
- [ ] `data/run_log.json` contains `{"runs": []}`
- [ ] All 13 tests pass
- [ ] Schedule registered and shows correct next run time
- [ ] `data/.linkedin_person_id` will be created automatically on first run

---

## Notes

- LinkedIn access token expires in 60 days. Check `data/run_log.json` for `401` errors. Regenerate token at LinkedIn Developer Portal and update `.env`.
- If a day is skipped (quality gate failure), `run_log.json` will show `"success": false` with reason.
- To see what has been posted: `cat data/posted_topics.json`
- To see run history: `cat data/run_log.json`
