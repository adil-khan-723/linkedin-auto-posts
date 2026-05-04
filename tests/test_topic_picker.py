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
    # iacguard posted 30 days ago — cooldown expired, should be available
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
    assert "iacguard" in result["topic"]


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
