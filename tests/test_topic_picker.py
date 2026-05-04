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
        }
    ]
}

MONDAY = datetime.datetime(2026, 5, 4)    # weekday() == 0
WEDNESDAY = datetime.datetime(2026, 5, 6) # weekday() == 2


def _setup(tmp_path, posted_topics=None):
    scraped = tmp_path / "scraped.json"
    posted = tmp_path / "posted.json"
    output = tmp_path / "selected.json"
    scraped.write_text(json.dumps(SAMPLE_SCRAPED))
    posted.write_text(json.dumps({"posted": posted_topics or []}))
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


def test_monday_falls_back_to_self_generated_when_github_exhausted(tmp_path, monkeypatch):
    used_topic = "iacguard: Terraform blast radius analyzer"
    scraped, posted, output = _setup(tmp_path, [{"topic": used_topic}])
    monkeypatch.setattr(topic_picker, "SCRAPED_FILE", str(scraped))
    monkeypatch.setattr(topic_picker, "POSTED_FILE", str(posted))
    monkeypatch.setattr(topic_picker, "OUTPUT_FILE", str(output))

    with patch("topic_picker.datetime.datetime") as mock_dt:
        mock_dt.utcnow.return_value = MONDAY
        topic_picker.pick_topic()

    result = json.loads(output.read_text())
    assert result["source"] == "self-generated"


def test_skips_used_self_generated_topics(tmp_path, monkeypatch):
    first_self_gen = topic_picker.SELF_GENERATED_TOPICS[0]["topic"]
    scraped, posted, output = _setup(tmp_path, [{"topic": first_self_gen}])
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
