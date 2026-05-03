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
    for field in ["topic", "angle", "repo", "source", "selected_at"]:
        assert field in result, f"Missing field: {field}"
