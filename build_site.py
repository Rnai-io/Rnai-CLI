# -*- coding: utf-8 -*-
"""Script to build static web app files for Netlify deployment"""
import sys
from pathlib import Path

def build():
    out_dir = Path("public")
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. Try importing from rnai_cli.ui
    try:
        from rnai_cli.ui import HTML, MANIFEST_JSON, SW_JS
        (out_dir / "index.html").write_text(HTML, encoding="utf-8")
        (out_dir / "manifest.json").write_text(MANIFEST_JSON, encoding="utf-8")
        (out_dir / "sw.js").write_text(SW_JS, encoding="utf-8")
        (out_dir / "_redirects").write_text("/*  /index.html  200\n", encoding="utf-8")
        print(f"✅ WebApp static build complete in '{out_dir.resolve()}'")
        return
    except Exception as e:
        print(f"⚠️ Import warning ({e}), checking pre-built public files...")

    # 2. Fallback: Check if public/index.html already exists in repo
    if (out_dir / "index.html").exists():
        (out_dir / "_redirects").write_text("/*  /index.html  200\n", encoding="utf-8")
        print(f"✅ Pre-built public/ files verified for Netlify deployment.")
        return

    print("❌ Error: index.html not found.")
    sys.exit(1)

if __name__ == "__main__":
    build()
