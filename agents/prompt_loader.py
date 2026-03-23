"""
Utility for loading and rendering Jinja2 prompt templates.
All LLM prompts in Tastyz Bakery are managed as .j2 files in the prompts/ directory.
"""

import logging
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"

_jinja_env = Environment(
    loader=FileSystemLoader(str(PROMPTS_DIR)),
    undefined=StrictUndefined,
    trim_blocks=True,
    lstrip_blocks=True,
)


def render_prompt(template_name: str, **kwargs: object) -> str:
    """
    Load and render a Jinja2 prompt template.

    Args:
        template_name: filename of the .j2 template (e.g. "chatbot_system.j2")
        **kwargs: variables to inject into the template

    Returns:
        Rendered prompt string
    """
    try:
        template = _jinja_env.get_template(template_name)
        rendered = template.render(**kwargs)
        logger.debug("Rendered prompt template: %s", template_name)
        return rendered
    except Exception as exc:
        logger.error("Failed to render prompt template %s: %s", template_name, exc)
        raise
