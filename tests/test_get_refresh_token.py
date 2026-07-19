from unittest.mock import patch, MagicMock
import get_refresh_token as grt


def test_handle_tokens_sets_access_token_secret_when_no_refresh():
    data = {"access_token": "acc_123"}
    with patch("get_refresh_token.subprocess.run") as run:
        run.return_value = MagicMock(returncode=0)
        grt.handle_tokens(data, repo="owner/repo", set_secret=True)

    # LINKEDIN_ACCESS_TOKEN secret set with the access token piped to stdin
    calls = [c for c in run.call_args_list if "LINKEDIN_ACCESS_TOKEN" in c[0][0]]
    assert len(calls) == 1
    cmd = calls[0][0][0]
    assert cmd[:3] == ["gh", "secret", "set"]
    assert "--repo" in cmd and "owner/repo" in cmd
    assert calls[0][1]["input"] == "acc_123"


def test_handle_tokens_sets_refresh_secret_when_present():
    data = {"access_token": "acc_123", "refresh_token": "ref_456"}
    with patch("get_refresh_token.subprocess.run") as run:
        run.return_value = MagicMock(returncode=0)
        grt.handle_tokens(data, repo="owner/repo", set_secret=True)

    names = {c[0][0][3] for c in run.call_args_list}  # gh secret set <NAME>
    assert "LINKEDIN_REFRESH_TOKEN" in names


def test_handle_tokens_no_secret_call_when_set_secret_false():
    data = {"access_token": "acc_123"}
    with patch("get_refresh_token.subprocess.run") as run:
        grt.handle_tokens(data, repo="owner/repo", set_secret=False)
    run.assert_not_called()
