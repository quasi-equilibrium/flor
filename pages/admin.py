"""
Admin Sayfası - PAİY (Planlı Alanlar İmar Yönetmeliği) Kısıtlarını Düzenleme
Madde referansları: 5, 23, 28, 29, 30, 31, 32, 34, 38, 39
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import json

from core.building_codes import BuildingCodes, DEFAULT_CONFIG_PATH

st.set_page_config(page_title="Ayarlar - PAİY Kısıtları", page_icon="⚙️", layout="wide")

st.title("⚙️ PAİY Yapı Yönetmeliği Ayarları")
st.caption("Planlı Alanlar İmar Yönetmeliği uyumlu kısıtlar. Değişiklikler kaydedildiğinde hemen uygulanır.")
st.info(
    "📋 **Kaynak:** PAİY Madde 29 (piyes min), Madde 30 (dolaşım), Madde 31 (merdiven), "
    "Madde 32 (ışıklık), Madde 34 (asansör), Madde 38 (korkuluk), Madde 39 (kapı/pencere). "
    "Son değişiklikler: RG 32838 (11.03.2025), RG 32985 (13.08.2025). "
    "Eskişehir özelinde parselin bağlı olduğu idarenin imar durumu ek kısıt getirebilir."
)

# ── Yükle ─────────────────────────────────────────────────────────────────────

codes = BuildingCodes()

# ══════════════════════════════════════════════════════════════════════════════
# A) ODA / PİYES MİNİMUMLARI (Madde 29)
# ══════════════════════════════════════════════════════════════════════════════

st.header("A) Oda / Piyes Minimumları (Madde 29)")
st.caption("Her oda tipi için PAİY'nin zorunlu kıldığı minimum alan ve dar kenar ölçüsü.")

# Minimum Alanlar
st.subheader("Minimum Alanlar (m²)")
min_areas = codes.raw.get("min_areas", {})
col1, col2, col3 = st.columns(3)
updated_min_areas = {}
items = list(min_areas.items())
for i, (key, val) in enumerate(items):
    with [col1, col2, col3][i % 3]:
        display = key.replace("_", " ").title()
        updated_min_areas[key] = st.number_input(
            f"{display}", value=float(val or 0), min_value=0.0, step=0.5,
            key=f"min_area_{key}",
        )

# Minimum Genişlikler
st.subheader("Minimum Dar Kenar (m)")
min_widths = codes.raw.get("min_widths", {})
col1, col2, col3 = st.columns(3)
updated_min_widths = {}
items = list(min_widths.items())
for i, (key, val) in enumerate(items):
    with [col1, col2, col3][i % 3]:
        display = key.replace("_", " ").title()
        updated_min_widths[key] = st.number_input(
            f"{display}", value=float(val), min_value=0.0, step=0.1,
            key=f"min_width_{key}",
        )

# ══════════════════════════════════════════════════════════════════════════════
# B) DOLAŞIM ALANLARI (Madde 29, 30)
# ══════════════════════════════════════════════════════════════════════════════

st.divider()
st.header("B) Dolaşım Alanları (Madde 29, 30)")

col1, col2, col3 = st.columns(3)
with col1:
    bldg_corr_w = st.number_input(
        "Bina koridoru min genişlik (m)",
        value=codes.raw.get("building_corridor", {}).get("min_width", 1.50),
        step=0.1, key="bldg_corr_w",
        help="Madde 30(1): Bina giriş holü ve koridor min genişlik"
    )
with col2:
    apt_corr_w = st.number_input(
        "Daire içi koridor min genişlik (m)",
        value=codes.raw.get("apartment_corridor", {}).get("min_width", 1.20),
        step=0.1, key="apt_corr_w",
        help="Madde 29(3): Daire içi hol/koridor"
    )
with col3:
    bldg_entry_w = st.number_input(
        "Bina giriş holü min genişlik (m)",
        value=codes.raw.get("building_entry", {}).get("min_width", 1.50),
        step=0.1, key="bldg_entry_w",
        help="Madde 30(1): Ana merdiven ve asansöre ulaşana kadar"
    )

# ══════════════════════════════════════════════════════════════════════════════
# C) MERDİVEN (Madde 31, 38)
# ══════════════════════════════════════════════════════════════════════════════

st.divider()
st.header("C) Merdiven Ölçüleri (Madde 31, 38)")

stairs = codes.raw.get("stairs", {})

col1, col2 = st.columns(2)
with col1:
    st.markdown("**Şaft Boyutları**")
    stairs_w = st.number_input(
        "Merdiven evi genişlik (m)", value=stairs.get("width", 3.00),
        step=0.1, key="stairs_w",
        help="2×kol + boşluk + duvarlar. Şaft tam kat yüksekliğini kaplar."
    )
    stairs_l = st.number_input(
        "Merdiven evi uzunluk (m)", value=stairs.get("length", 6.00),
        step=0.1, key="stairs_l",
        help="Basamak sembolü bu alan içinde çizilir"
    )
    stairs_arm = st.number_input(
        "Kol genişliği - konut (m)", value=stairs.get("arm_width", 1.20),
        step=0.05, key="stairs_arm",
        help="Madde 31(1a): Konut ortak merdiven kolu min genişlik"
    )
with col2:
    st.markdown("**Basamak ve Korkuluk**")
    stairs_riser_elev = st.number_input(
        "Rıht max - asansörlü (m)", value=stairs.get("riser_max_with_elevator", 0.18),
        step=0.01, key="stairs_riser_e",
        help="Madde 31(2a): Asansörlü binada max rıht"
    )
    stairs_riser_no = st.number_input(
        "Rıht max - asansörsüz (m)", value=stairs.get("riser_max_without_elevator", 0.16),
        step=0.01, key="stairs_riser_n",
        help="Madde 31(2a): Asansörsüz binada max rıht"
    )
    stairs_tread = st.number_input(
        "Basamak genişliği min (m)", value=stairs.get("tread_min", 0.27),
        step=0.01, key="stairs_tread",
        help="Madde 31(2b): Formül: 2a+b = 60-64 cm"
    )
    stairs_handrail = st.number_input(
        "Korkuluk yüksekliği min (m)", value=stairs.get("handrail_height", 1.10),
        step=0.05, key="stairs_handrail",
        help="Madde 38(1): Merdiven ve boşluklarda korkuluk"
    )

# ══════════════════════════════════════════════════════════════════════════════
# D) ASANSÖR (Madde 34)
# ══════════════════════════════════════════════════════════════════════════════

st.divider()
st.header("D) Asansör Gereksinimleri (Madde 34)")

elev = codes.raw.get("elevator_shaft", {})

col1, col2 = st.columns(2)
with col1:
    st.markdown("**Kuyu Boyutları**")
    elev_w = st.number_input(
        "Kuyu genişlik (m)", value=elev.get("width", 2.50),
        step=0.1, key="elev_w",
        help="Kuyu tam kat yüksekliğini kaplar"
    )
    elev_l = st.number_input(
        "Kuyu uzunluk (m)", value=elev.get("length", 2.50),
        step=0.1, key="elev_l",
    )
    st.caption(f"Kabin min: {elev.get('cabin_min_width', 1.20)}m × "
               f"{elev.get('cabin_min_length', 1.50)}m "
               f"(alan min {elev.get('cabin_min_area', 1.80)}m²)")
    st.caption(f"Kapı net geçiş min: {elev.get('door_min_width', 0.90)}m")

with col2:
    st.markdown("**Zorunluluklar**")
    st.caption(f"• {elev.get('min_floors_space', 3)} kat: asansör **yeri** zorunlu")
    st.caption(f"• {elev.get('min_floors_required', 4)}+ kat: asansör **montajı** zorunlu")
    st.caption(f"• {elev.get('dual_elevator_floors', 10)} kat veya "
               f"{elev.get('dual_elevator_apartments', 20)}+ daire: **çift asansör** zorunlu")
    st.caption(f"• {elev.get('fire_elevator_floors', 10)}+ kat: 1 asansör yangına dayanıklı")
    st.caption(f"• {elev.get('stretcher_min_floors', 10)}+ kat: sedye asansörü "
               f"(min {elev.get('stretcher_cabin_width', 1.20)}×{elev.get('stretcher_cabin_length', 2.10)}m)")

# ══════════════════════════════════════════════════════════════════════════════
# E) KAPI ve PENCERE (Madde 39)
# ══════════════════════════════════════════════════════════════════════════════

st.divider()
st.header("E) Kapı Boyutları (Madde 39)")

doors = codes.raw.get("doors", {})
col1, col2, col3, col4, col5 = st.columns(5)

updated_doors = {}
with col1:
    std = doors.get("standard", {})
    updated_doors["standard"] = {
        "width": st.number_input("Oda genişlik", value=std.get("width", 0.90), step=0.05, key="door_std_w"),
        "height": st.number_input("Oda yükseklik", value=std.get("height", 2.10), step=0.05, key="door_std_h"),
    }
with col2:
    bny = doors.get("banyo", {})
    updated_doors["banyo"] = {
        "width": st.number_input("Banyo genişlik", value=bny.get("width", 0.80) if isinstance(bny, dict) else 0.80, step=0.05, key="door_bny_w"),
        "height": st.number_input("Banyo yükseklik", value=bny.get("height", 2.10) if isinstance(bny, dict) else 2.10, step=0.05, key="door_bny_h"),
    }
with col3:
    wc = doors.get("tuvalet", {})
    updated_doors["tuvalet"] = {
        "width": st.number_input("WC genişlik", value=wc.get("width", 0.80) if isinstance(wc, dict) else 0.80, step=0.05, key="door_wc_w"),
        "height": st.number_input("WC yükseklik", value=wc.get("height", 2.10) if isinstance(wc, dict) else 2.10, step=0.05, key="door_wc_h"),
    }
with col4:
    grs = doors.get("giris", {})
    updated_doors["giris"] = {
        "width": st.number_input("Daire giriş gen.", value=grs.get("width", 1.00) if isinstance(grs, dict) else 1.00, step=0.05, key="door_grs_w"),
        "height": st.number_input("Daire giriş yük.", value=grs.get("height", 2.10) if isinstance(grs, dict) else 2.10, step=0.05, key="door_grs_h"),
    }
with col5:
    bg = doors.get("bina_giris", {})
    updated_doors["bina_giris"] = {
        "width": st.number_input("Bina giriş gen.", value=bg.get("width", 1.50) if isinstance(bg, dict) else 1.50, step=0.05, key="door_bg_w"),
        "height": st.number_input("Bina giriş yük.", value=bg.get("height", 2.10) if isinstance(bg, dict) else 2.10, step=0.05, key="door_bg_h"),
    }

# ══════════════════════════════════════════════════════════════════════════════
# F) DUVAR ve KAT YÜKSEKLİKLERİ (Madde 28)
# ══════════════════════════════════════════════════════════════════════════════

st.divider()
st.header("F) Duvar ve Kat Yükseklikleri (Madde 28)")

col1, col2 = st.columns(2)

with col1:
    st.markdown("**Duvar Kalınlıkları (m)**")
    walls = codes.raw.get("walls", {})
    new_outer = st.number_input("Dış duvar", value=walls.get("outer_thickness", 0.25), step=0.05, key="wall_outer")
    new_inner = st.number_input("İç duvar", value=walls.get("inner_thickness", 0.15), step=0.05, key="wall_inner")
    new_carrier = st.number_input("Taşıyıcı duvar", value=walls.get("carrier_thickness", 0.20), step=0.05, key="wall_carrier")

with col2:
    st.markdown("**Kat Yükseklikleri (m)**")
    floor_h = st.number_input(
        "Brüt kat yüksekliği", value=codes.raw.get("floor_height", 2.80),
        step=0.1, key="floor_h",
    )
    floor_h_max = st.number_input(
        "Brüt kat yüksekliği MAX", value=codes.raw.get("floor_height_max", 3.60),
        step=0.1, key="floor_h_max",
        help="Madde 28(1c): Konut bölgelerinde döşemeden döşemeye max"
    )
    ceil_h = st.number_input(
        "Min tavan yüksekliği (iskân)", value=codes.raw.get("min_ceiling_height", 2.60),
        step=0.1, key="ceil_h",
        help="Madde 28(4): İskân edilen katta min net tavan yüksekliği"
    )
    wet_ceil_h = st.number_input(
        "Islak hacim tavan yüksekliği", value=codes.raw.get("wet_area_ceiling_height", 2.20),
        step=0.1, key="wet_ceil_h",
        help="Madde 28(5): Banyo, WC, koridor gibi alanlarda min"
    )

# ══════════════════════════════════════════════════════════════════════════════
# G) PARSEL KISITLARI (Madde 23, 32)
# ══════════════════════════════════════════════════════════════════════════════

st.divider()
st.header("G) Parsel ve Yerleşim (Madde 23, 32)")

setbacks = codes.raw.get("setbacks", {})
lightwell = codes.raw.get("lightwell", {})

col1, col2 = st.columns(2)
with col1:
    st.markdown("**Bahçe Mesafeleri (m)**")
    sb_front = st.number_input("Ön bahçe min", value=setbacks.get("front_min", 5.00), step=0.5, key="sb_front",
                                help="Madde 23(1a)")
    sb_side = st.number_input("Yan bahçe min", value=setbacks.get("side_min", 3.00), step=0.5, key="sb_side",
                               help="Madde 23(1b): 4 kata kadar")
    sb_rear = st.number_input("Arka bahçe min", value=setbacks.get("rear_min", 3.00), step=0.5, key="sb_rear",
                               help="Madde 23(1c): 4 kata kadar")
    sb_inc = st.number_input("Kat artış çekmesi", value=setbacks.get("floor_increment", 0.50), step=0.1, key="sb_inc",
                              help="Madde 23(1ç): 4 katın üzerinde her kat için +m")

with col2:
    st.markdown("**Işıklık ve Hava Bacası**")
    lw_small_edge = st.number_input("Işıklık kenar (1-6 kat)", value=lightwell.get("small_min_edge", 1.50), step=0.1, key="lw_se",
                                     help="Madde 32(2a)")
    lw_small_area = st.number_input("Işıklık alan (1-6 kat)", value=lightwell.get("small_min_area", 4.50), step=0.5, key="lw_sa")
    lw_large_edge = st.number_input("Işıklık kenar (7+ kat)", value=lightwell.get("large_min_edge", 2.00), step=0.1, key="lw_le",
                                     help="Madde 32(2b)")
    lw_large_area = st.number_input("Işıklık alan (7+ kat)", value=lightwell.get("large_min_area", 9.00), step=0.5, key="lw_la")
    as_w = st.number_input("Hava bacası genişlik", value=lightwell.get("air_shaft_width", 0.60), step=0.1, key="as_w",
                            help="Madde 32(3): Sadece banyo/WC havalandırması")

# ══════════════════════════════════════════════════════════════════════════════
# H) YANGIN / ISLAK HACİM BİLGİ
# ══════════════════════════════════════════════════════════════════════════════

st.divider()
st.header("H) Yangın ve Islak Hacim Kuralları")
st.caption("Bu kurallar salt okunur referans bilgisidir.")

fire = codes.raw.get("fire_safety", {})
wet_rules = codes.raw.get("wet_area_rules", {})

st.markdown(f"""
| Kural | Açıklama |
|-------|----------|
| Karma merdiven ayrımı | Madde 31(5): Konut + ticaret karma kullanımda ayrı merdiven evi zorunlu |
| Yangın asansörü | Madde 34(4): 10+ katlı binalarda 1 asansör yangına dayanıklı/güç kaynaklı |
| Havalandırma ayrımı | Madde 29(6): Mutfak/oda bacaları WC/banyo boşluğuna açılamaz |
| Elektrik güvenliği | Madde 29(7): Islak hacim altına enerji odası kurulamaz |
| Kaçış mesafesi | Yangın Yönetmeliği referansı (~30m) - PAİY'de doğrudan belirtilmez |
| Erişilebilirlik | TS 9111 ve Asansör Yönetmeliği (2014/33/AB) referansı |
""")

# ══════════════════════════════════════════════════════════════════════════════
# KAYDET
# ══════════════════════════════════════════════════════════════════════════════

st.divider()

if st.button("💾 Değişiklikleri Kaydet", type="primary", use_container_width=True):
    # A) Oda minimumları
    codes.raw["min_areas"] = updated_min_areas
    codes.raw["min_widths"] = updated_min_widths

    # B) Dolaşım
    codes.raw["building_corridor"]["min_width"] = bldg_corr_w
    codes.raw["apartment_corridor"]["min_width"] = apt_corr_w
    codes.raw["building_entry"]["min_width"] = bldg_entry_w

    # C) Merdiven (kullanıcı alanları güncelle, geri kalanını koru)
    codes.raw["stairs"]["width"] = stairs_w
    codes.raw["stairs"]["length"] = stairs_l
    codes.raw["stairs"]["arm_width"] = stairs_arm
    codes.raw["stairs"]["riser_max_with_elevator"] = stairs_riser_elev
    codes.raw["stairs"]["riser_max_without_elevator"] = stairs_riser_no
    codes.raw["stairs"]["tread_min"] = stairs_tread
    codes.raw["stairs"]["handrail_height"] = stairs_handrail

    # D) Asansör
    codes.raw["elevator_shaft"]["width"] = elev_w
    codes.raw["elevator_shaft"]["length"] = elev_l

    # E) Kapılar (note alanlarını koru)
    for door_key, door_val in updated_doors.items():
        codes.raw["doors"][door_key] = door_val
    # Note alanlarını koru
    for note_key in ["standard_note", "islak_hacim_note", "giris_note", "bina_giris_note"]:
        pass  # JSON'da zaten var, silinmez

    # F) Duvar ve yükseklikler
    codes.raw["walls"]["outer_thickness"] = new_outer
    codes.raw["walls"]["inner_thickness"] = new_inner
    codes.raw["walls"]["carrier_thickness"] = new_carrier
    codes.raw["floor_height"] = floor_h
    codes.raw["floor_height_max"] = floor_h_max
    codes.raw["min_ceiling_height"] = ceil_h
    codes.raw["wet_area_ceiling_height"] = wet_ceil_h

    # G) Parsel
    codes.raw.setdefault("setbacks", {})
    codes.raw["setbacks"]["front_min"] = sb_front
    codes.raw["setbacks"]["side_min"] = sb_side
    codes.raw["setbacks"]["rear_min"] = sb_rear
    codes.raw["setbacks"]["floor_increment"] = sb_inc

    codes.raw.setdefault("lightwell", {})
    codes.raw["lightwell"]["small_min_edge"] = lw_small_edge
    codes.raw["lightwell"]["small_min_area"] = lw_small_area
    codes.raw["lightwell"]["large_min_edge"] = lw_large_edge
    codes.raw["lightwell"]["large_min_area"] = lw_large_area
    codes.raw["lightwell"]["air_shaft_width"] = as_w

    codes.save()
    st.success("Ayarlar kaydedildi!")
    st.cache_resource.clear()

# ── JSON görünümü ─────────────────────────────────────────────────────────────

st.divider()
with st.expander("🔧 Ham JSON (gelişmiş düzenleme)"):
    raw_json = json.dumps(codes.raw, ensure_ascii=False, indent=2)
    edited = st.text_area("JSON", value=raw_json, height=400)
    if st.button("JSON'dan Güncelle"):
        try:
            new_data = json.loads(edited)
            codes._data = new_data
            codes.save()
            st.success("JSON'dan güncellendi!")
            st.cache_resource.clear()
        except json.JSONDecodeError as e:
            st.error(f"Geçersiz JSON: {e}")
