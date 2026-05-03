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
