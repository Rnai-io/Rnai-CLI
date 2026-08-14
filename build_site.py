# -*- coding: utf-8 -*-
"""Script to build static web app files for Netlify deployment"""
import json
from pathlib import Path
from rnai_cli.ui import HTML, MANIFEST_JSON, SW_JS

def build():
    out_dir = Path("public")
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. index.html
    (out_dir / "index.html").write_text(HTML, encoding="utf-8")

    # 2. manifest.json
    (out_dir / "manifest.json").write_text(MANIFEST_JSON, encoding="utf-8")

    # 3. sw.js
    (out_dir / "sw.js").write_text(SW_JS, encoding="utf-8")

    # 4. _redirects for Netlify SPA
    (out_dir / "_redirects").write_text("/*  /index.html  200\n", encoding="utf-8")

    print(f"✅ WebApp static build complete in '{out_dir.resolve()}'")

if __name__ == "__main__":
    build()
