"""
Generate a Mermaid architecture diagram for the selected topic.
Writes PNG to data/diagram.png and Mermaid source to data/diagram.mmd.
Exits 0 on success, 1 on failure (pipeline continues without diagram).
"""
import sys
import json
import base64
import os
import requests
from pathlib import Path

SELECTED_TOPIC_FILE = "data/selected_topic.json"
DIAGRAM_PNG = "data/diagram.png"
DIAGRAM_MMD = "data/diagram.mmd"

MERMAID_INK_URL = "https://mermaid.ink/img/{encoded}?type=png&width=1200&height=628&bgColor=!white"

# Topics where a diagram adds no value
SKIP_KEYWORDS = ["culture", "career", "mindset", "hiring", "team", "management", "burnout"]


def load_topic():
    try:
        with open(SELECTED_TOPIC_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def should_skip(topic_data):
    topic_str = (topic_data.get("topic", "") + " " + topic_data.get("angle", "")).lower()
    return any(kw in topic_str for kw in SKIP_KEYWORDS)


def generate_mermaid(topic_data):
    topic = topic_data.get("topic", "")
    angle = topic_data.get("angle", "")

    # Derive a focused diagram from the topic
    # Heuristic: pick diagram type based on content
    text = (topic + " " + angle).lower()

    if any(kw in text for kw in ["pipeline", "cicd", "ci/cd", "workflow", "deploy"]):
        diagram = _cicd_diagram(topic, angle)
    elif any(kw in text for kw in ["kubernetes", "k8s", "cluster", "pod", "service"]):
        diagram = _k8s_diagram(topic, angle)
    elif any(kw in text for kw in ["monitor", "alert", "observ", "grafana", "prometheus", "log"]):
        diagram = _observability_diagram(topic, angle)
    elif any(kw in text for kw in ["docker", "container", "image", "registry"]):
        diagram = _docker_diagram(topic, angle)
    elif any(kw in text for kw in ["terraform", "infra", "iac", "provision"]):
        diagram = _iac_diagram(topic, angle)
    else:
        diagram = _generic_flow(topic, angle)

    return diagram


def _cicd_diagram(topic, angle):
    # Detect AI/LLM involvement
    has_ai = any(kw in (topic + angle).lower() for kw in ["ai", "llm", "copilot", "gpt", "openai", "claude"])
    has_slack = "slack" in (topic + angle).lower()
    has_jenkins = "jenkins" in (topic + angle).lower()
    has_github = "github" in (topic + angle).lower()

    ci_node = "Jenkins" if has_jenkins else ("GitHub Actions" if has_github else "CI System")

    nodes = []
    nodes.append(f'    Dev["Developer"] -->|push| VCS["Git Repo"]')
    nodes.append(f'    VCS -->|trigger| CI["{ci_node}"]')
    nodes.append(f'    CI -->|run| Build["Build & Test"]')
    nodes.append(f'    Build -->|on failure| Analyzer["Failure Analyzer"]')

    if has_ai:
        nodes.append(f'    Analyzer -->|logs| LLM["LLM Analysis"]')
        if has_slack:
            nodes.append(f'    LLM -->|summary + approval| Slack["Slack"]')
            nodes.append(f'    Slack -->|approved| Deploy["Deploy"]')
        else:
            nodes.append(f'    LLM -->|root cause| Report["Report"]')
    else:
        nodes.append(f'    Analyzer -->|report| Notify["Notify Team"]')

    nodes.append(f'    Build -->|on success| Deploy["Deploy"]')

    return "flowchart LR\n" + "\n".join(nodes)


def _k8s_diagram(topic, angle):
    return """flowchart TB
    User["User"] -->|request| Ingress["Ingress"]
    Ingress --> SVC["Service"]
    SVC --> Pod1["Pod A"]
    SVC --> Pod2["Pod B"]
    Pod1 & Pod2 --> PVC["PersistentVolume"]
    HPA["HPA"] -.->|scale| Pod1
    HPA -.->|scale| Pod2"""


def _observability_diagram(topic, angle):
    has_prom = "prometheus" in (topic + angle).lower()
    has_grafana = "grafana" in (topic + angle).lower()

    collector = "Prometheus" if has_prom else "Metrics Collector"
    viz = "Grafana" if has_grafana else "Dashboard"

    return f"""flowchart LR
    App["App"] -->|metrics| {collector.replace(' ','_')}["{collector}"]
    App -->|logs| Loki["Loki / ELK"]
    App -->|traces| Tempo["Tempo / Jaeger"]
    {collector.replace(' ','_')} --> {viz.replace(' ','_')}["{viz}"]
    Loki --> {viz.replace(' ','_')}
    Tempo --> {viz.replace(' ','_')}
    {viz.replace(' ','_')} -->|alert| PagerDuty["PagerDuty / Slack"]"""


def _docker_diagram(topic, angle):
    return """flowchart LR
    Code["Source Code"] -->|docker build| Image["Docker Image"]
    Image -->|docker push| Registry["Container Registry"]
    Registry -->|docker pull| Dev["Dev Env"]
    Registry -->|docker pull| Prod["Prod Env"]"""


def _iac_diagram(topic, angle):
    return """flowchart LR
    HCL["Terraform HCL"] -->|plan| Plan["terraform plan"]
    Plan -->|review| Approve{"Approved?"}
    Approve -->|yes| Apply["terraform apply"]
    Approve -->|no| Fix["Fix & Re-plan"]
    Apply --> Cloud["Cloud Resources"]
    Cloud -.->|state| Backend["Remote State"]"""


def _generic_flow(topic, angle):
    return """flowchart LR
    Input["Trigger"] --> Process["Pipeline"]
    Process -->|success| Output["Artifact / Deploy"]
    Process -->|failure| Alert["Alert / Retry"]"""


def render_png(mermaid_src):
    encoded = base64.urlsafe_b64encode(mermaid_src.encode()).decode()
    url = MERMAID_INK_URL.format(encoded=encoded)
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    if resp.headers.get("content-type", "").startswith("image"):
        return resp.content
    raise RuntimeError(f"mermaid.ink returned non-image: {resp.headers.get('content-type')}")


def main():
    os.makedirs("data", exist_ok=True)
    topic_data = load_topic()

    if not topic_data:
        print("No selected topic found — skipping diagram")
        sys.exit(0)

    if should_skip(topic_data):
        print(f"Topic not diagram-suitable — skipping")
        sys.exit(0)

    mermaid_src = generate_mermaid(topic_data)

    Path(DIAGRAM_MMD).write_text(mermaid_src)
    print(f"Mermaid source:\n{mermaid_src}\n")

    print("Rendering via mermaid.ink...")
    try:
        png_data = render_png(mermaid_src)
    except Exception as e:
        print(f"Render failed: {e} — skipping diagram")
        # Remove any stale diagram so poster knows to skip
        Path(DIAGRAM_PNG).unlink(missing_ok=True)
        sys.exit(0)

    Path(DIAGRAM_PNG).write_bytes(png_data)
    print(f"Diagram saved: {DIAGRAM_PNG} ({len(png_data)} bytes)")


if __name__ == "__main__":
    main()
