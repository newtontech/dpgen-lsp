"""Template management for dpgen input files.

LLM Wiki: wiki/synthesis/openqc-agent-context.md
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# Templates are stored in this directory
_TEMPLATES_DIR = Path(__file__).parent


def _load_index() -> dict[str, Any]:
    """Load template index from index.json.

LLM Wiki: wiki/synthesis/openqc-agent-context.md
"""
    index_path = _TEMPLATES_DIR / "index.json"
    with open(index_path, "r", encoding="utf-8") as f:
        return json.load(f)


def list_templates(kind: str | None = None) -> list[dict[str, Any]]:
    """
    List available templates.
    
    Args:
        kind: Filter by template kind ('param' or 'machine'). If None, return all.
    
    Returns:
        List of template metadata dictionaries.

LLM Wiki: wiki/synthesis/openqc-agent-context.md
"""
    index = _load_index()
    templates = index.get("templates", [])
    
    if kind is None:
        return templates
    
    return [t for t in templates if t.get("kind") == kind]


def get_template(key: str, kind: str | None = None) -> dict[str, Any] | None:
    """
    Get template metadata by key.
    
    Args:
        key: Template key (e.g., 'vasp-ch4', 'lebesgue-v2')
        kind: Optional kind filter for faster lookup
    
    Returns:
        Template metadata dict or None if not found.

LLM Wiki: wiki/synthesis/openqc-agent-context.md
"""
    templates = list_templates(kind)
    
    for template in templates:
        if template.get("key") == key:
            return template
    
    return None


def read_template(key: str, kind: str | None = None) -> str | None:
    """
    Read template file content.
    
    Args:
        key: Template key
        kind: Optional kind filter
    
    Returns:
        Template file content as string, or None if not found.

LLM Wiki: wiki/synthesis/openqc-agent-context.md
"""
    template = get_template(key, kind)
    if template is None:
        return None
    
    resource_path = _TEMPLATES_DIR / template["resource"]
    if not resource_path.exists():
        return None
    
    with open(resource_path, "r", encoding="utf-8") as f:
        return f.read()


def write_template(
    template_key: str,
    output_path: Path,
    kind: str | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    """
    Write template to specified path.
    
    Args:
        template_key: Template key
        output_path: Output file path
        kind: Optional kind filter
        overwrite: Whether to overwrite existing file
    
    Returns:
        Result dictionary with 'success', 'path', and optional 'error' fields.

LLM Wiki: wiki/synthesis/openqc-agent-context.md
"""
    template = get_template(template_key, kind)
    
    if template is None:
        return {
            "success": False,
            "error": f"Template '{template_key}' not found",
            "path": str(output_path)
        }
    
    content = read_template(template_key, kind)
    if content is None:
        return {
            "success": False,
            "error": f"Template file not found: {template.get('resource')}",
            "path": str(output_path)
        }
    
    if output_path.exists() and not overwrite:
        return {
            "success": False,
            "error": f"File already exists: {output_path}",
            "path": str(output_path)
        }
    
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        return {
            "success": True,
            "path": str(output_path),
            "template": template_key,
            "kind": template.get("kind")
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "path": str(output_path)
        }
