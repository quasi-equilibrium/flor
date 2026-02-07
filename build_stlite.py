#!/usr/bin/env python3
"""
stlite Build Script
-------------------
Tum Python ve config dosyalarini okuyarak tek bir docs/index.html dosyasi olusturur.
Bu HTML dosyasi GitHub Pages'te statik olarak host edilir ve Streamlit uygulamasini
tamamen tarayicida (Pyodide/WebAssembly uzerinden) calistirir.

Kullanim:
    python build_stlite.py

Cikti:
    docs/index.html
"""

import json
import os
from pathlib import Path

# ── Proje kok dizini ─────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent
DOCS_DIR = PROJECT_ROOT / "docs"
OUTPUT_FILE = DOCS_DIR / "index.html"

# stlite CDN versiyonu
STLITE_VERSION = "0.76.0"

# Pyodide'da yuklenmesi gereken paketler
# NOT: shapely, networkx, ezdxf kullanilmiyor veya Pyodide'da yok
REQUIREMENTS = ["numpy", "matplotlib", "pydantic"]

# ── Gomulecek dosyalar ───────────────────────────────────────────────────────
# (dosya_yolu_proje_icinde, stlite_icindeki_hedef_yol)
FILES_TO_EMBED = [
    # Ana uygulama
    ("app.py", "app.py"),

    # Core modulleri
    ("core/__init__.py", "core/__init__.py"),
    ("core/models.py", "core/models.py"),
    ("core/building_codes.py", "core/building_codes.py"),
    ("core/building_layout.py", "core/building_layout.py"),
    ("core/apartment_layout.py", "core/apartment_layout.py"),
    ("core/genetic.py", "core/genetic.py"),
    ("core/fitness.py", "core/fitness.py"),
    ("core/furniture.py", "core/furniture.py"),
    ("core/slicing_tree.py", "core/slicing_tree.py"),
    ("core/walls.py", "core/walls.py"),
    ("core/core_placer.py", "core/core_placer.py"),
    ("core/validator.py", "core/validator.py"),
    ("core/room_defaults.py", "core/room_defaults.py"),
    ("core/corridor.py", "core/corridor.py"),
    ("core/envelope.py", "core/envelope.py"),

    # Export modulleri
    ("export/__init__.py", "export/__init__.py"),
    ("export/svg_renderer.py", "export/svg_renderer.py"),
    ("export/dxf_exporter.py", "export/dxf_exporter.py"),

    # Sayfalar
    ("pages/admin.py", "pages/admin.py"),

    # Config
    ("config/building_codes_tr.json", "config/building_codes_tr.json"),
]


def escape_for_js(content: str) -> str:
    """Python/JSON icerigini JavaScript template literal icinde guvenli hale getir."""
    # Backtick ve ${} escape et (JS template literal icinde ozel karakterler)
    content = content.replace("\\", "\\\\")  # Once backslash
    content = content.replace("`", "\\`")     # Backtick
    content = content.replace("${", "\\${")   # Template literal interpolation
    return content


def read_file(path: Path) -> str:
    """Dosyayi oku, yoksa bos string don."""
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def build_files_object() -> str:
    """stlite mount() icin files objesi olustur."""
    lines = []
    for src_path, target_path in FILES_TO_EMBED:
        full_path = PROJECT_ROOT / src_path
        content = read_file(full_path)
        escaped = escape_for_js(content)
        lines.append(f'          "{target_path}": `{escaped}`')

    return ",\n".join(lines)


def build_html() -> str:
    """Tam index.html icerigini olustur."""
    files_js = build_files_object()
    requirements_js = json.dumps(REQUIREMENTS)

    return f'''<!DOCTYPE html>
<html lang="tr">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Kat Plani Uretici - PAiY Uyumlu</title>
  <link
    rel="stylesheet"
    href="https://cdn.jsdelivr.net/npm/@stlite/browser@{STLITE_VERSION}/build/stlite.css"
  />
  <style>
    /* Yukleme ekrani */
    #loading-screen {{
      position: fixed;
      top: 0; left: 0; right: 0; bottom: 0;
      background: #1a1a2e;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      z-index: 9999;
      color: #e0e0e0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }}
    #loading-screen h1 {{
      font-size: 1.8rem;
      margin-bottom: 1rem;
      color: #ffffff;
    }}
    #loading-screen p {{
      font-size: 1rem;
      opacity: 0.7;
      margin: 0.3rem 0;
    }}
    .spinner {{
      width: 40px;
      height: 40px;
      border: 4px solid rgba(255,255,255,0.2);
      border-top-color: #4fc3f7;
      border-radius: 50%;
      animation: spin 1s linear infinite;
      margin-bottom: 1.5rem;
    }}
    @keyframes spin {{
      to {{ transform: rotate(360deg); }}
    }}
  </style>
</head>
<body>
  <!-- Yukleme ekrani -->
  <div id="loading-screen">
    <div class="spinner"></div>
    <h1>Kat Plani Uretici</h1>
    <p>Python ortami yukleniyor (Pyodide)...</p>
    <p style="font-size: 0.85rem; opacity: 0.5;">Ilk acilista 15-30 saniye surebilir</p>
  </div>

  <div id="root"></div>

  <script src="https://cdn.jsdelivr.net/npm/@stlite/browser@{STLITE_VERSION}/build/stlite.js"></script>

  <script>
    // Yukleme ekranini stlite hazir olunca kaldir
    const observer = new MutationObserver(function(mutations) {{
      const stApp = document.querySelector('.stApp');
      if (stApp) {{
        const loadingScreen = document.getElementById('loading-screen');
        if (loadingScreen) {{
          loadingScreen.style.transition = 'opacity 0.5s';
          loadingScreen.style.opacity = '0';
          setTimeout(() => loadingScreen.remove(), 500);
        }}
        observer.disconnect();
      }}
    }});
    observer.observe(document.body, {{ childList: true, subtree: true }});

    stlite.mount(
      {{
        requirements: {requirements_js},
        entrypoint: "app.py",
        files: {{
{files_js}
        }},
        streamlitConfig: {{
          "theme.base": "light",
          "client.toolbarMode": "viewer",
          "browser.gatherUsageStats": false
        }}
      }},
      document.getElementById("root")
    );
  </script>
</body>
</html>'''


def main():
    # docs/ klasoru olustur
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    # HTML olustur
    html = build_html()

    # Yaz
    OUTPUT_FILE.write_text(html, encoding="utf-8")

    # Bilgi
    size_kb = OUTPUT_FILE.stat().st_size / 1024
    n_files = len(FILES_TO_EMBED)
    print(f"Build tamamlandi!")
    print(f"  Dosya: {OUTPUT_FILE}")
    print(f"  Boyut: {size_kb:.1f} KB")
    print(f"  Gomulu dosya: {n_files}")
    print(f"  Paketler: {', '.join(REQUIREMENTS)}")
    print(f"\nGitHub Pages icin 'docs/' klasorunu kaynak olarak secin.")
    print(f"Lokal test icin: python -m http.server 8080 -d docs/")


if __name__ == "__main__":
    main()
