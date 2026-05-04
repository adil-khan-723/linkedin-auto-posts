import os
import sys
import json
import requests
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

LINKEDIN_API = "https://api.linkedin.com/v2"
POSTED_FILE = "data/posted_topics.json"
RUN_LOG_FILE = "data/run_log.json"
SELECTED_TOPIC_FILE = "data/selected_topic.json"
PERSON_ID_FILE = "data/.linkedin_person_id"
DIAGRAM_PNG = "data/diagram.png"


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


def _try_upload_diagram(token, person_id):
    if not Path(DIAGRAM_PNG).exists():
        return None
    try:
        from linkedin_image_uploader import upload_image
        asset_urn = upload_image(token, person_id, DIAGRAM_PNG)
        print(f"Diagram uploaded: {asset_urn}")
        return asset_urn
    except Exception as e:
        print(f"Diagram upload failed (posting text only): {e}")
        return None


def post_to_linkedin(text, token, person_id):
    asset_urn = _try_upload_diagram(token, person_id)

    if asset_urn:
        content = {
            "shareCommentary": {"text": text},
            "shareMediaCategory": "IMAGE",
            "media": [
                {
                    "status": "READY",
                    "description": {"text": "Architecture diagram"},
                    "media": asset_urn,
                    "title": {"text": "Diagram"},
                }
            ],
        }
    else:
        content = {
            "shareCommentary": {"text": text},
            "shareMediaCategory": "NONE",
        }

    payload = {
        "author": f"urn:li:person:{person_id}",
        "lifecycleState": "PUBLISHED",
        "specificContent": {"com.linkedin.ugc.ShareContent": content},
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
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
    if not resp.ok:
        raise RuntimeError(
            f"LinkedIn POST {resp.status_code}: {resp.text} | "
            f"x-li-uuid={resp.headers.get('x-li-uuid')} "
            f"x-li-route-key={resp.headers.get('x-li-route-key')}"
        )
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
