"""Deterministic fixtures, not a language model or a relevance benchmark."""

import hashlib
import json
import math
import re

MARKER = "[DEMO FIXTURE]"
DOCUMENTS = {
    "demo-storage.txt": "AlopexDB connects LlamaIndex. LlamaIndex connects GraphRAG. GraphRAG connects AlopexDB.",
    "demo-service.txt": "GraphRAG connects SearchDemo. SearchDemo connects AlopexDB. AlopexDB connects GraphRAG.",
}


def embed(text: str) -> list[float]:
    """Return a stable 64-dimensional token hash vector without downloads."""
    values = [0.0] * 64
    for token in re.findall(r"\w+", text.lower()) or ["empty"]:
        values[int.from_bytes(hashlib.sha256(token.encode()).digest()[:4], "big") % 64] += 1
    norm = math.sqrt(sum(value * value for value in values))
    return [value / norm for value in values]


def complete_fixture(prompt: str) -> str:
    """Handle only known pipeline prompts; unexpected prompts fail closed."""
    if prompt.lstrip().startswith("Extract entities and relationships"):
        text = prompt.split("\nText: ", 1)[1]
        pairs = re.findall(r"(\w+) connects (\w+)\.", text)
        if not pairs:
            raise ValueError("Demo input must contain 'Source connects Target.' sentences")
        names = sorted({name for pair in pairs for name in pair})
        return json.dumps({
            "entities": [{"name": name, "type": "DemoComponent"} for name in names],
            "relationships": [{"source": a, "target": b, "type": "connects",
                               "description": f"{a} connects {b}"} for a, b in pairs],
        })
    if "\nテキスト: " in prompt:
        text = prompt.split("\nテキスト: ", 1)[1].split("\n\n", 1)[0]
        return json.dumps({"community_id": 0, "summary": MARKER + " " + text,
                           "key_entities": sorted(set(re.findall(r"\w+(?= connects)", text)))})
    if "## Context Information:" in prompt:
        context = prompt.split("## Context Information:", 1)[1].split("## User", 1)[0]
        return MARKER + " local context: " + context.strip()
    if "Context Data:\n" in prompt:
        context = prompt.split("Context Data:\n", 1)[1].split("\nUser Question:", 1)[0]
        points = []
        for line in context.splitlines():
            fields = line.split("|")
            if len(fields) == 5 and fields[0] != "id":
                points.append({"description": fields[2], "score": 80, "report_ids": [fields[0]]})
        if not points:
            raise ValueError("Demo map received no community reports")
        return json.dumps({"points": points})
    if "Analyst Reports:\n" in prompt:
        context = prompt.split("Analyst Reports:\n", 1)[1].split("\nUser Question:", 1)[0]
        if MARKER not in context:
            raise ValueError("Demo reduce received no fixture evidence")
        return MARKER + " global reports: " + context.strip()
    raise ValueError("Unsupported demo prompt; no external provider fallback")
