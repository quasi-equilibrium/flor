# Kat Plani Uretici

Cok katli konut (apartman) binalari icin otomatik kat plani ureteci.
PAiY (Planli Alanlar Imar Yonetmeligi) uyumlu kisitlarla calisir.

**AI kullanilmaz** - tamamen algoritmik plan uretimi.

## Canli Demo

**[https://KULLANICI.github.io/floorplan-web/](https://KULLANICI.github.io/floorplan-web/)**

> Ilk acilista 15-30 saniye bekleyiniz (Python ortami tarayicida yukleniyor).
> Chrome, Edge veya Safari kullanin. Firefox desteklenmez.

## Ozellikler

- 40m x 20m'ye kadar bina boyutlari
- Kat basina 2-10 daire
- PAiY Madde 29/31/34 uyumlu oda minimumlari
- Otomatik merdiven ve asansor yerlestirme (cift asansor dahil)
- 4 alternatif plan uretimi
- PNG indirme
- Yapi yonetmeligi ayarlarini duzenleme (admin sayfasi)

## Teknoloji

- **Python / Streamlit** - uygulama framework'u
- **stlite** - Streamlit'i tarayicida calistirir (Pyodide/WebAssembly)
- **matplotlib** - plan cizimi
- **pydantic** - veri modelleri

## Lokal Gelistirme

```bash
# Python 3.10+ gerekli
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Web Build (GitHub Pages)

```bash
# docs/index.html olustur
python build_stlite.py

# Lokal test
python -m http.server 8080 -d docs/
# Tarayicida http://localhost:8080 ac
```

GitHub Pages icin repo ayarlarindan:
- Settings > Pages > Source: "Deploy from a branch"
- Branch: `main`, Folder: `/docs`

## Proje Yapisi

```
floorplan-web/
  app.py                  # Ana Streamlit uygulamasi
  core/                   # Algoritma modulleri
    models.py             # Pydantic veri modelleri
    building_codes.py     # PAiY kisitlari
    building_layout.py    # Bina duzeni (cekirdek + koridor + daireler)
    apartment_layout.py   # Daire ici oda yerlestirme
    genetic.py            # Plan uretim motoru
    ...
  export/
    svg_renderer.py       # matplotlib ile plan cizimi
    dxf_exporter.py       # DXF export (lokal'de calisir)
  pages/
    admin.py              # Yonetmelik ayarlari sayfasi
  config/
    building_codes_tr.json  # PAiY sayisal kisitlari
  build_stlite.py         # Web build script
  docs/
    index.html            # Uretilen statik site
```

## Lisans

MIT
