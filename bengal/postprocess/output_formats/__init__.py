"""
Output formats generation package for Bengal SSG.

Generates alternative output formats for pages to enable:
- Client-side search (JSON index)
- AI/LLM discovery (plain text format)
- Programmatic access (JSON API)

Structure:
- generator.py: OutputFormatsGenerator facade
- incremental.py: Cache merge, fingerprints, and site-wide skip
- site_wide.py: Site-wide format generation
- paths.py: Path, hash, and fingerprint helpers
- support.py: Config normalization, filtering, and progress
- json_generator.py: Per-page JSON files
- txt_generator.py: Per-page LLM text files
- index_generator.py: Site-wide index.json
- llm_generator.py: Site-wide llm-full.txt
- llms_txt_generator.py: Site-wide llms.txt (curated overview per llmstxt.org)
- utils.py: Shared utilities

Configuration (bengal.toml):
[output_formats]
    enabled = true
    per_page = ["json", "llm_txt"]
    site_wide = ["index_json", "llm_full", "llms_txt"]

"""

from bengal.postprocess.output_formats.base import BaseOutputGenerator
from bengal.postprocess.output_formats.generator import OutputFormatsGenerator
from bengal.postprocess.output_formats.index_generator import SiteIndexGenerator
from bengal.postprocess.output_formats.json_generator import PageJSONGenerator
from bengal.postprocess.output_formats.llm_generator import SiteLlmTxtGenerator
from bengal.postprocess.output_formats.llms_txt_generator import SiteLlmsTxtGenerator
from bengal.postprocess.output_formats.lunr_index_generator import LunrIndexGenerator
from bengal.postprocess.output_formats.md_generator import PageMarkdownGenerator
from bengal.postprocess.output_formats.txt_generator import PageTxtGenerator

__all__ = [
    "BaseOutputGenerator",
    "LunrIndexGenerator",
    "OutputFormatsGenerator",
    "PageJSONGenerator",
    "PageMarkdownGenerator",
    "PageTxtGenerator",
    "SiteIndexGenerator",
    "SiteLlmTxtGenerator",
    "SiteLlmsTxtGenerator",
]
