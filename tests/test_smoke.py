"""Repository-level sanity checks."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_required_paths_exist():
    expected = [
        ROOT / "backend" / "app" / "main.py",
        ROOT / "frontend" / "package.json",
        ROOT / "docker-compose.yml",
        ROOT / "prompts" / "rag_answer.txt",
        ROOT / "sample_data" / "documents" / "leave_policy.md",
        ROOT / ".github" / "workflows" / "ci.yml",
    ]
    missing = [str(p) for p in expected if not p.exists()]
    assert not missing, missing
