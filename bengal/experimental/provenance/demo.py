#!/usr/bin/env python3
"""
Demo script for provenance-based incremental builds.

This demonstrates the core concept without modifying Bengal's main code.

Usage:
    cd /path/to/bengal/site
    python -m bengal.experimental.provenance.demo

Or from bengal repo root:
    python bengal/experimental/provenance/demo.py
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from datetime import datetime


def demo_provenance_tracking():
    """Demonstrate provenance tracking with a simple example."""
    
    print("=" * 60)
    print("Provenance-Based Incremental Build Demo")
    print("=" * 60)
    print()
    
    # Import our prototype
    from bengal.experimental.provenance import (
        ProvenanceStore,
        ProvenanceTracker,
    )
    
    # Create a temporary site for demo
    with tempfile.TemporaryDirectory() as tmpdir:
        site_root = Path(tmpdir)
        
        # Create demo content
        content_dir = site_root / "content"
        content_dir.mkdir()
        
        templates_dir = site_root / "templates"
        templates_dir.mkdir()
        
        data_dir = site_root / "data"
        data_dir.mkdir()
        
        # Create files
        (content_dir / "about.md").write_text("""---
title: About Us
---

# About Us

We are a great company!
""")
        
        (content_dir / "blog.md").write_text("""---
title: Blog
tags: [news, updates]
---

# Blog

Latest news here.
""")
        
        (templates_dir / "base.html").write_text("""<!DOCTYPE html>
<html>
<head><title>{{ title }}</title></head>
<body>{% block content %}{% endblock %}</body>
</html>
""")
        
        (templates_dir / "page.html").write_text("""{% extends "base.html" %}
{% block content %}
<article>{{ content }}</article>
{% endblock %}
""")
        
        (data_dir / "team.yaml").write_text("""- name: Alice
  role: Engineer
- name: Bob
  role: Designer
""")
        
        # Initialize provenance store
        cache_dir = site_root / ".bengal" / "provenance"
        store = ProvenanceStore(cache_dir)
        tracker = ProvenanceTracker(store, site_root, build_id="demo-001")
        
        print("📁 Demo site created with:")
        print("   - content/about.md")
        print("   - content/blog.md")
        print("   - templates/base.html")
        print("   - templates/page.html")
        print("   - data/team.yaml")
        print()
        
        # ========================================
        # BUILD 1: Initial build (cold cache)
        # ========================================
        print("=" * 60)
        print("BUILD 1: Initial build (cold cache)")
        print("=" * 60)
        print()
        
        for page_name in ["about.md", "blog.md"]:
            page_path = f"content/{page_name}"
            
            print(f"🔨 Building {page_path}...")
            
            # Check cache (should miss)
            if tracker.is_fresh(page_path):
                print(f"   ✅ Cache hit! Skipping.")
            else:
                print(f"   ❌ Cache miss. Rendering...")
                
                # Track provenance during "render"
                with tracker.track(page_path) as ctx:
                    # Read inputs (automatically tracked)
                    content = ctx.read_file(content_dir / page_name, input_type="content")
                    template = ctx.read_template(templates_dir / "page.html")
                    base_template = ctx.read_template(templates_dir / "base.html")
                    
                    if page_name == "about.md":
                        # About page uses team data
                        team = ctx.read_data("team.yaml")
                    
                    # Simulate render
                    html = f"<html>{content}</html>"
                    ctx.set_output(html)
                
                print(f"   📊 {ctx.provenance.summary()}")
        
        tracker.save()
        print()
        print(f"💾 Provenance saved to {cache_dir}")
        print()
        
        # Show stats
        stats = tracker.stats()
        print("📈 Store stats:")
        for k, v in stats.items():
            print(f"   {k}: {v}")
        print()
        
        # ========================================
        # BUILD 2: No changes (warm cache)
        # ========================================
        print("=" * 60)
        print("BUILD 2: No changes (warm cache)")
        print("=" * 60)
        print()
        
        for page_name in ["about.md", "blog.md"]:
            page_path = f"content/{page_name}"
            
            if tracker.is_fresh(page_path):
                print(f"✅ {page_path}: Cache hit! Skipping render.")
            else:
                print(f"❌ {page_path}: Needs rebuild.")
        print()
        
        # ========================================
        # BUILD 3: Content change
        # ========================================
        print("=" * 60)
        print("BUILD 3: Content file changed")
        print("=" * 60)
        print()
        
        # Modify about.md
        (content_dir / "about.md").write_text("""---
title: About Us (Updated!)
---

# About Us

We are an AMAZING company!
""")
        print("✏️  Modified content/about.md")
        print()
        
        for page_name in ["about.md", "blog.md"]:
            page_path = f"content/{page_name}"
            
            if tracker.is_fresh(page_path):
                print(f"✅ {page_path}: Cache hit!")
            else:
                print(f"❌ {page_path}: Needs rebuild.")
                
                # Rebuild
                with tracker.track(page_path) as ctx:
                    content = ctx.read_file(content_dir / page_name, input_type="content")
                    template = ctx.read_template(templates_dir / "page.html")
                    base_template = ctx.read_template(templates_dir / "base.html")
                    if page_name == "about.md":
                        team = ctx.read_data("team.yaml")
                    html = f"<html>{content}</html>"
                    ctx.set_output(html)
                print(f"   Rebuilt with {ctx.provenance.input_count} inputs")
        
        tracker.save()
        print()
        
        # ========================================
        # BUILD 4: Template change (affects all pages!)
        # ========================================
        print("=" * 60)
        print("BUILD 4: Template change (SUBVENANCE query)")
        print("=" * 60)
        print()
        
        # Modify base template
        (templates_dir / "base.html").write_text("""<!DOCTYPE html>
<html>
<head>
    <title>{{ title }} | My Site</title>
    <meta charset="utf-8">
</head>
<body>{% block content %}{% endblock %}</body>
</html>
""")
        print("✏️  Modified templates/base.html")
        print()
        
        # SUBVENANCE QUERY: What pages use base.html?
        from bengal.experimental.provenance.core_types import hash_file
        
        template_hash = hash_file(templates_dir / "base.html")
        affected = store.get_affected_by(template_hash)
        
        # Note: We need the OLD hash to find affected pages
        # In practice, we'd compare old vs new hash
        print("🔍 Subvenance query: What pages used base.html?")
        
        # For demo, check all pages since template changed
        for page_name in ["about.md", "blog.md"]:
            page_path = f"content/{page_name}"
            
            # In real impl, template hash in provenance wouldn't match anymore
            print(f"   ❌ {page_path}: Template changed, needs rebuild")
        print()
        
        # ========================================
        # LINEAGE: Debug what produced a page
        # ========================================
        print("=" * 60)
        print("LINEAGE: What inputs produced about.md?")
        print("=" * 60)
        print()
        
        for line in tracker.get_lineage("content/about.md"):
            print(line)
        print()
        
        print("=" * 60)
        print("Demo complete!")
        print("=" * 60)


def demo_with_real_site():
    """Demo with a real Bengal site (if available)."""
    
    # Try to find a Bengal site
    candidates = [
        Path.cwd() / "site",
        Path.cwd().parent / "site",
        Path(__file__).parent.parent.parent.parent / "site",
    ]
    
    site_root = None
    for candidate in candidates:
        if (candidate / "content").exists() and (candidate / "config").exists():
            site_root = candidate
            break
    
    if site_root is None:
        print("No Bengal site found. Run demo_provenance_tracking() instead.")
        return
    
    print(f"Found Bengal site at: {site_root}")
    print()
    
    from bengal.experimental.provenance import (
        ProvenanceStore,
        ProvenanceTracker,
    )
    
    # Initialize
    cache_dir = site_root / ".bengal" / "provenance"
    store = ProvenanceStore(cache_dir)
    tracker = ProvenanceTracker(store, site_root)
    
    # Find some content files
    content_dir = site_root / "content"
    content_files = list(content_dir.glob("**/*.md"))[:5]
    
    print(f"Tracking provenance for {len(content_files)} pages...")
    print()
    
    for content_file in content_files:
        rel_path = str(content_file.relative_to(site_root))
        
        with tracker.track(rel_path) as ctx:
            ctx.read_file(content_file, input_type="content")
        
        print(f"  {rel_path}: {ctx.provenance.input_count} inputs")
    
    tracker.save()
    print()
    print(f"Provenance saved to {cache_dir}")
    print()
    print("Stats:", tracker.stats())


if __name__ == "__main__":
    if "--real" in sys.argv:
        demo_with_real_site()
    else:
        demo_provenance_tracking()
