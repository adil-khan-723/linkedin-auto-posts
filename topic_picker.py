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
