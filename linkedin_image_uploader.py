"""
Upload a PNG to LinkedIn and return the asset URN.
Used by linkedin_poster.py to attach a diagram to a post.
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

LINKEDIN_API = "https://api.linkedin.com/v2"
DIAGRAM_PNG = "data/diagram.png"


def upload_image(token, person_id, png_path=DIAGRAM_PNG):
    """Register upload, PUT bytes, return asset URN string."""

    # Step 1: Register upload
    register_payload = {
        "registerUploadRequest": {
            "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
            "owner": f"urn:li:person:{person_id}",
            "serviceRelationships": [
                {
                    "relationshipType": "OWNER",
                    "identifier": "urn:li:userGeneratedContent",
                }
            ],
        }
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
    }

    resp = requests.post(
        f"{LINKEDIN_API}/assets?action=registerUpload",
        headers=headers,
        json=register_payload,
        timeout=30,
    )
    if not resp.ok:
        raise RuntimeError(
            f"LinkedIn registerUpload {resp.status_code}: {resp.text}"
        )

    data = resp.json()["value"]
    asset_urn = data["asset"]
    upload_url = data["uploadMechanism"][
        "com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"
    ]["uploadUrl"]

    # Step 2: Upload image bytes
    with open(png_path, "rb") as f:
        png_bytes = f.read()

    put_resp = requests.put(
        upload_url,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "image/png",
        },
        data=png_bytes,
        timeout=60,
    )
    if not put_resp.ok:
        raise RuntimeError(
            f"LinkedIn image PUT {put_resp.status_code}: {put_resp.text}"
        )

    return asset_urn
