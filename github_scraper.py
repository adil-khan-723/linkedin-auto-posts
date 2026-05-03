import os
import json
import base64
import requests
from datetime import datetime

GITHUB_USERNAME = "adil-khan-723"
GITHUB_API = "https://api.github.com"
OUTPUT_FILE = "data/scraped_data.json"
README_MAX_CHARS = 3000

DEVOPS_REPOS = [
    "cicd-ai-copilot",
    "iacguard",
    "k8s-observability-stack",
    "kubernetes-sample-voting-app-project-tls",
    "K8s-RBAC",
    "EKS-Terraform-Provisioning",
    "slim-vs-alpine",
    "terraform_project2_refactored",
    "terraform-project2-moudlarized",
    "microservices",
    "terraform-aws-infra",
    "terraform-docker-ci-cd-project3",
    "kubernetes-sample-voting-app-project1",
]


def fetch_repo_data(repo_name):
    headers = {"Accept": "application/vnd.github.v3+json"}

    repo_resp = requests.get(
        f"{GITHUB_API}/repos/{GITHUB_USERNAME}/{repo_name}", headers=headers
    )
    if repo_resp.status_code != 200:
        return None
    repo = repo_resp.json()

    readme = ""
    readme_resp = requests.get(
        f"{GITHUB_API}/repos/{GITHUB_USERNAME}/{repo_name}/readme", headers=headers
    )
    if readme_resp.status_code == 200:
        readme = base64.b64decode(readme_resp.json()["content"]).decode(
            "utf-8", errors="ignore"
        )[:README_MAX_CHARS]

    commits = []
    commits_resp = requests.get(
        f"{GITHUB_API}/repos/{GITHUB_USERNAME}/{repo_name}/commits",
        headers=headers,
        params={"per_page": 10},
    )
    if commits_resp.status_code == 200:
        commits = [
            c["commit"]["message"].split("\n")[0] for c in commits_resp.json()
        ]

    return {
        "name": repo_name,
        "description": repo.get("description", ""),
        "language": repo.get("language", ""),
        "readme": readme,
        "recent_commits": commits,
        "updated_at": repo.get("updated_at", ""),
    }


def scrape():
    repos = []
    for repo_name in DEVOPS_REPOS:
        data = fetch_repo_data(repo_name)
        if data:
            repos.append(data)

    output = {"repos": repos, "scraped_at": datetime.utcnow().isoformat()}

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Scraped {len(repos)} repos → {OUTPUT_FILE}")


if __name__ == "__main__":
    scrape()
