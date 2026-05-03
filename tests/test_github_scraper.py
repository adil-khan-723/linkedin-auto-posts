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
