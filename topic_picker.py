import json
import os
import datetime
from datetime import timedelta, datetime as _dt

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


REPO_COOLDOWN_DAYS = 28  # same repo not reused within 4 weeks


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


def _repos_on_cooldown(posted_entries, now):
    """Return set of repo names posted within the last REPO_COOLDOWN_DAYS."""
    cutoff = now - timedelta(days=REPO_COOLDOWN_DAYS)
    on_cooldown = set()
    for entry in posted_entries:
        repo = entry.get("repo")
        posted_at = entry.get("posted_at")
        if not repo or not posted_at:
            continue
        try:
            when = _dt.fromisoformat(posted_at)
        except ValueError:
            continue
        if when >= cutoff:
            on_cooldown.add(repo)
    return on_cooldown


def pick_topic():
    scraped = load_json(SCRAPED_FILE, {"repos": []})
    posted = load_json(POSTED_FILE, {"posted": []})

    now = datetime.datetime.utcnow()
    used_self = {p["topic"] for p in posted.get("posted", []) if not p.get("repo")}

    # Monday (weekday 0) = GitHub repo topic; Wed/Fri = self-generated
    is_monday = now.weekday() == 0

    if is_monday:
        cooldown = _repos_on_cooldown(posted.get("posted", []), now)
        candidates = extract_repo_topics(scraped["repos"])
        available = [t for t in candidates if t["repo"] not in cooldown]
        if not available:
            available = candidates
        if available:
            selected = {**available[0], "source": "github"}
        else:
            # No GitHub repos available — fall through to self-generated
            unused_self = [t for t in SELF_GENERATED_TOPICS if t["topic"] not in used_self]
            if not unused_self:
                unused_self = SELF_GENERATED_TOPICS
            selected = {**unused_self[0], "source": "self-generated"}
    else:
        unused_self = [t for t in SELF_GENERATED_TOPICS if t["topic"] not in used_self]
        if not unused_self:
            unused_self = SELF_GENERATED_TOPICS
        selected = {**unused_self[0], "source": "self-generated"}

    result = {
        "topic": selected["topic"],
        "angle": selected["angle"],
        "repo": selected.get("repo"),
        "source": selected["source"],
        "selected_at": datetime.datetime.utcnow().isoformat(),
    }

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(result, f, indent=2)

    print(f"Selected: {result['topic']} (source: {result['source']})")


if __name__ == "__main__":
    pick_topic()
