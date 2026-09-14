import json
import pytest
from unittest.mock import patch, MagicMock
import datetime
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
        },
        {
            "name": "k8s-observability-stack",
            "description": "Prometheus and Grafana stack",
            "language": "YAML",
            "readme": "# K8s Observability",
            "recent_commits": ["feat: add ServiceMonitor"],
            "updated_at": "2026-03-20",
        },
    ]
}

MONDAY = datetime.datetime(2026, 5, 4)    # weekday() == 0
WEDNESDAY = datetime.datetime(2026, 5, 6) # weekday() == 2


def _setup(tmp_path, posted_entries=None):
    scraped = tmp_path / "scraped.json"
    posted = tmp_path / "posted.json"
    output = tmp_path / "selected.json"
    scraped.write_text(json.dumps(SAMPLE_SCRAPED))
    posted.write_text(json.dumps({"posted": posted_entries or []}))
    return scraped, posted, output


def test_monday_selects_github_topic(tmp_path, monkeypatch):
    scraped, posted, output = _setup(tmp_path)
    monkeypatch.setattr(topic_picker, "SCRAPED_FILE", str(scraped))
    monkeypatch.setattr(topic_picker, "POSTED_FILE", str(posted))
    monkeypatch.setattr(topic_picker, "OUTPUT_FILE", str(output))

    with patch("topic_picker.datetime.datetime") as mock_dt:
        mock_dt.utcnow.return_value = MONDAY
        topic_picker.pick_topic()

    result = json.loads(output.read_text())
    assert result["source"] == "github"
    assert "iacguard" in result["topic"]


def test_wednesday_selects_self_generated(tmp_path, monkeypatch):
    scraped, posted, output = _setup(tmp_path)
    monkeypatch.setattr(topic_picker, "SCRAPED_FILE", str(scraped))
    monkeypatch.setattr(topic_picker, "POSTED_FILE", str(posted))
    monkeypatch.setattr(topic_picker, "OUTPUT_FILE", str(output))

    with patch("topic_picker.datetime.datetime") as mock_dt:
        mock_dt.utcnow.return_value = WEDNESDAY
        topic_picker.pick_topic()

    result = json.loads(output.read_text())
    assert result["source"] == "self-generated"


def test_monday_skips_repo_on_cooldown(tmp_path, monkeypatch):
    # iacguard posted 1 week ago — on cooldown; k8s-observability-stack should be picked
    recent = (MONDAY - datetime.timedelta(days=7)).isoformat()
    posted_entries = [{"repo": "iacguard", "topic": "iacguard: Terraform blast radius analyzer", "posted_at": recent}]
    scraped, posted, output = _setup(tmp_path, posted_entries)
    monkeypatch.setattr(topic_picker, "SCRAPED_FILE", str(scraped))
    monkeypatch.setattr(topic_picker, "POSTED_FILE", str(posted))
    monkeypatch.setattr(topic_picker, "OUTPUT_FILE", str(output))

    with patch("topic_picker.datetime.datetime") as mock_dt:
        mock_dt.utcnow.return_value = MONDAY
        topic_picker.pick_topic()

    result = json.loads(output.read_text())
    assert result["source"] == "github"
    assert "k8s-observability-stack" in result["topic"]


def test_monday_repo_available_after_cooldown(tmp_path, monkeypatch):
    # iacguard posted 30 days ago — cooldown expired, should be available again.
    # k8s-observability-stack is still on cooldown (posted 3 days ago) so it's
    # filtered out, isolating this test to cooldown-expiry behavior rather than
    # LRU-across-never-posted-repos behavior (covered separately).
    old = (MONDAY - datetime.timedelta(days=30)).isoformat()
    recent = (MONDAY - datetime.timedelta(days=3)).isoformat()
    posted_entries = [
        {"repo": "iacguard", "topic": "iacguard: Terraform blast radius analyzer", "posted_at": old},
        {"repo": "k8s-observability-stack", "topic": "k8s-observability-stack: Prometheus and Grafana stack", "posted_at": recent},
    ]
    scraped, posted, output = _setup(tmp_path, posted_entries)
    monkeypatch.setattr(topic_picker, "SCRAPED_FILE", str(scraped))
    monkeypatch.setattr(topic_picker, "POSTED_FILE", str(posted))
    monkeypatch.setattr(topic_picker, "OUTPUT_FILE", str(output))

    with patch("topic_picker.datetime.datetime") as mock_dt:
        mock_dt.utcnow.return_value = MONDAY
        topic_picker.pick_topic()

    result = json.loads(output.read_text())
    assert result["source"] == "github"
    assert "iacguard" in result["topic"]


def test_monday_prefers_never_posted_repo_over_cooldown_expired(tmp_path, monkeypatch):
    # iacguard posted 30 days ago (cooldown expired, so technically available);
    # k8s-observability-stack has never been posted at all. A never-posted repo
    # should win over re-posting one that's simply aged out of cooldown.
    old = (MONDAY - datetime.timedelta(days=30)).isoformat()
    posted_entries = [{"repo": "iacguard", "topic": "iacguard: Terraform blast radius analyzer", "posted_at": old}]
    scraped, posted, output = _setup(tmp_path, posted_entries)
    monkeypatch.setattr(topic_picker, "SCRAPED_FILE", str(scraped))
    monkeypatch.setattr(topic_picker, "POSTED_FILE", str(posted))
    monkeypatch.setattr(topic_picker, "OUTPUT_FILE", str(output))

    with patch("topic_picker.datetime.datetime") as mock_dt:
        mock_dt.utcnow.return_value = MONDAY
        topic_picker.pick_topic()

    result = json.loads(output.read_text())
    assert result["source"] == "github"
    assert "k8s-observability-stack" in result["topic"]


def test_skips_used_self_generated_topics(tmp_path, monkeypatch):
    first_self_gen = topic_picker.SELF_GENERATED_TOPICS[0]["topic"]
    posted_entries = [{"repo": None, "topic": first_self_gen, "posted_at": WEDNESDAY.isoformat()}]
    scraped, posted, output = _setup(tmp_path, posted_entries)
    monkeypatch.setattr(topic_picker, "SCRAPED_FILE", str(scraped))
    monkeypatch.setattr(topic_picker, "POSTED_FILE", str(posted))
    monkeypatch.setattr(topic_picker, "OUTPUT_FILE", str(output))

    with patch("topic_picker.datetime.datetime") as mock_dt:
        mock_dt.utcnow.return_value = WEDNESDAY
        topic_picker.pick_topic()

    result = json.loads(output.read_text())
    assert result["topic"] != first_self_gen


def test_all_self_generated_used_rotates_by_least_recently_posted(tmp_path, monkeypatch):
    # All 10 self-generated topics have been posted at least once. The pool
    # must not permanently pin to index 0 — it should keep rotating to
    # whichever topic was posted longest ago.
    topics = topic_picker.SELF_GENERATED_TOPICS
    base = WEDNESDAY - datetime.timedelta(days=100)
    posted_entries = [
        {"repo": None, "topic": t["topic"], "posted_at": (base + datetime.timedelta(days=i)).isoformat()}
        for i, t in enumerate(topics)
    ]
    scraped, posted, output = _setup(tmp_path, posted_entries)
    monkeypatch.setattr(topic_picker, "SCRAPED_FILE", str(scraped))
    monkeypatch.setattr(topic_picker, "POSTED_FILE", str(posted))
    monkeypatch.setattr(topic_picker, "OUTPUT_FILE", str(output))

    with patch("topic_picker.datetime.datetime") as mock_dt:
        mock_dt.utcnow.return_value = WEDNESDAY
        topic_picker.pick_topic()

    result = json.loads(output.read_text())
    assert result["topic"] == topics[0]["topic"]  # oldest posted_at

    # Repost topics[0] as the newest entry — next pick must move on to
    # topics[1], not reset back to topics[0] like the old bug did.
    posted_entries.append({"repo": None, "topic": topics[0]["topic"], "posted_at": WEDNESDAY.isoformat()})
    posted.write_text(json.dumps({"posted": posted_entries}))

    with patch("topic_picker.datetime.datetime") as mock_dt:
        mock_dt.utcnow.return_value = WEDNESDAY
        topic_picker.pick_topic()

    result2 = json.loads(output.read_text())
    assert result2["topic"] == topics[1]["topic"]
    assert result2["topic"] != topics[0]["topic"]


def test_output_has_required_fields(tmp_path, monkeypatch):
    scraped, posted, output = _setup(tmp_path)
    monkeypatch.setattr(topic_picker, "SCRAPED_FILE", str(scraped))
    monkeypatch.setattr(topic_picker, "POSTED_FILE", str(posted))
    monkeypatch.setattr(topic_picker, "OUTPUT_FILE", str(output))

    with patch("topic_picker.datetime.datetime") as mock_dt:
        mock_dt.utcnow.return_value = MONDAY
        topic_picker.pick_topic()

    result = json.loads(output.read_text())
    for field in ["topic", "angle", "repo", "source", "selected_at"]:
        assert field in result, f"Missing field: {field}"
