"""
Kat Planı Üretici v2 - Ana Streamlit Uygulaması
Çok daireli, mimari kalitede kat planı üretimi.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

from core.models import BuildingInput, RoomCountInput, CompassDirection
from core.building_codes import BuildingCodes
from core.genetic import generate_plans
from export.svg_renderer import render_plan

try:
    from export.dxf_exporter import export_to_dxf
    HAS_DXF = True
except ImportError:
    HAS_DXF = False

# ── Sayfa Yapılandırması ─────────────────────────────────────────────────────

st.set_page_config(
    page_title="Kat Planı Üretici",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

@st.cache_resource
def load_codes():
    return BuildingCodes()

codes = load_codes()

# ── Ana Sayfa ─────────────────────────────────────────────────────────────────

st.title("Kat Planı Üretici")
st.caption("Bina bilgilerini girin, 4 farklı alternatif kat planı üretelim. AI kullanılmaz - algoritmik.")

# ── Giriş Formu ──────────────────────────────────────────────────────────────

col_left, col_right = st.columns([1, 1])

with col_left:
    st.subheader("Bina Boyutları")

    input_method = st.radio(
        "Boyut giriş yöntemi",
        ["Kenar uzunlukları", "Toplam m²"],
        horizontal=True,
    )

    if input_method == "Kenar uzunlukları":
        long_side = st.number_input("Uzun kenar (m)", min_value=10.0, max_value=200.0, value=40.0, step=1.0)
        short_side = st.number_input("Kısa kenar (m)", min_value=8.0, max_value=100.0, value=20.0, step=1.0)
    else:
        total_m2 = st.number_input("Toplam alan (m²)", min_value=100.0, max_value=10000.0, value=800.0, step=50.0)
        aspect = st.slider("En/boy oranı", min_value=1.0, max_value=3.0, value=2.0, step=0.1)
        long_side = (total_m2 * aspect) ** 0.5
        short_side = total_m2 / long_side
        st.info(f"Hesaplanan: {long_side:.1f}m x {short_side:.1f}m = {long_side * short_side:.0f} m²")

    # Dikdörtgen ön izleme
    st.markdown("**Bina Ön İzleme:**")
    fig_p, ax_p = plt.subplots(figsize=(4, 2.5))
    rect_patch = mpatches.FancyBboxPatch(
        (0, 0), long_side, short_side,
        boxstyle="round,pad=0.1", facecolor="#E3F2FD", edgecolor="#1565C0", linewidth=2,
    )
    ax_p.add_patch(rect_patch)
    ax_p.set_xlim(-2, long_side + 2)
    ax_p.set_ylim(-2, short_side + 2)
    ax_p.set_aspect("equal")
    ax_p.text(long_side / 2, -1, f"{long_side:.1f} m", ha="center", fontsize=10)
    ax_p.text(-1, short_side / 2, f"{short_side:.1f} m", ha="center", fontsize=10, rotation=90)
    ax_p.text(long_side / 2, short_side / 2, f"{long_side * short_side:.0f} m²",
              ha="center", va="center", fontsize=14, fontweight="bold", color="#1565C0")
    ax_p.axis("off")
    st.pyplot(fig_p, use_container_width=True)
    plt.close(fig_p)

    # Yön seçimi
    st.subheader("Yön (Pusula)")
    north_option = st.selectbox(
        "Üst kenar hangi yöne bakıyor?",
        options=[
            ("Kuzey", CompassDirection.NORTH),
            ("Güney", CompassDirection.SOUTH),
            ("Doğu", CompassDirection.EAST),
            ("Batı", CompassDirection.WEST),
        ],
        format_func=lambda x: x[0],
        index=0,
    )
    north_facing = north_option[1]

with col_right:
    st.subheader("Bina Özellikleri")

    col_a, col_b = st.columns(2)
    with col_a:
        apartments_per_floor = st.number_input(
            "Katta kaç daire?", min_value=1, max_value=10, value=2,
        )
    with col_b:
        has_elevator = st.checkbox("Asansör var", value=True)

    num_floors = st.number_input("Toplam kat (zemin dahil)", min_value=1, max_value=30, value=5)
    if num_floors > 1:
        st.info("Not: Şu an tek kat planı üretilecek. Çok kat desteği ileride.")

    st.divider()
    st.subheader("Her Daire İçin Oda Sayıları")

    col_a, col_b = st.columns(2)
    with col_a:
        n_salon = st.number_input("Salon", min_value=0, max_value=5, value=1)
        n_yatak = st.number_input("Yatak Odası", min_value=0, max_value=10, value=2)
        n_oda = st.number_input("Oda (genel)", min_value=0, max_value=10, value=0)

    with col_b:
        n_mutfak = st.number_input("Mutfak", min_value=0, max_value=3, value=1)
        n_banyo = st.number_input("Banyo", min_value=0, max_value=5, value=1)
        n_tuvalet = st.number_input("WC", min_value=0, max_value=5, value=1)

    total_rooms = n_salon + n_yatak + n_oda + n_mutfak + n_banyo + n_tuvalet
    st.metric("Daire Başına Oda", total_rooms)
    st.metric("Toplam Daire", apartments_per_floor)
    st.metric("Kat Alanı", f"{long_side * short_side:.0f} m²")

# ── Tasarla Butonu ────────────────────────────────────────────────────────────

st.divider()

if st.button("🏗️  Planları Üret", type="primary", use_container_width=True):
    if total_rooms == 0:
        st.error("En az 1 oda seçmelisiniz.")
    else:
        building = BuildingInput(
            long_side=long_side,
            short_side=short_side,
            north_facing=north_facing,
            num_floors=num_floors,
            has_elevator=has_elevator,
            apartments_per_floor=apartments_per_floor,
        )
        room_counts = RoomCountInput(
            salon=n_salon, yatak_odasi=n_yatak, oda=n_oda,
            mutfak=n_mutfak, banyo=n_banyo, tuvalet=n_tuvalet,
        )

        # PAİY uyumluluk kontrolleri
        from core.building_layout import compute_building_layout
        zones = compute_building_layout(building, codes)
        if zones.warnings:
            for w in zones.warnings:
                if w.startswith("⚠️"):
                    st.warning(w)
                else:
                    st.info(w)

        with st.spinner("Planlar üretiliyor..."):
            plans = generate_plans(building, room_counts, codes, n_alternatives=4)

        if not plans:
            st.error("Plan üretilemedi. Farklı boyutlar deneyin.")
        else:
            st.success(f"{len(plans)} alternatif plan üretildi!")
            st.session_state["plans"] = plans

# ── Planları Göster ───────────────────────────────────────────────────────────

if "plans" in st.session_state:
    plans = st.session_state["plans"]

    st.divider()
    st.subheader("Alternatif Planlar")

    cols = st.columns(2)
    for i, plan in enumerate(plans[:4]):
        with cols[i % 2]:
            fig = render_plan(plan, figsize=(10, 7))
            st.pyplot(fig, use_container_width=True)
            plt.close(fig)

            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                if st.button(f"🔍 Büyüt", key=f"zoom_{i}"):
                    st.session_state["zoomed_plan"] = i
            with col_btn2:
                if HAS_DXF:
                    dxf_bytes = export_to_dxf(plan)
                    if dxf_bytes:
                        st.download_button(
                            f"📥 DXF İndir",
                            data=dxf_bytes,
                            file_name=f"kat_plani_{plan.plan_id}.dxf",
                            mime="application/dxf",
                            key=f"dxf_{i}",
                        )
                else:
                    # PNG indirme (stlite/Pyodide icin DXF yoksa)
                    import io
                    buf = io.BytesIO()
                    fig_dl = render_plan(plan, figsize=(16, 12))
                    fig_dl.savefig(buf, format="png", dpi=150, bbox_inches="tight")
                    plt.close(fig_dl)
                    st.download_button(
                        f"📥 PNG İndir",
                        data=buf.getvalue(),
                        file_name=f"kat_plani_{plan.plan_id}.png",
                        mime="image/png",
                        key=f"png_{i}",
                    )

    if "zoomed_plan" in st.session_state:
        idx = st.session_state["zoomed_plan"]
        if idx < len(plans):
            st.divider()
            st.subheader(f"Detaylı Görünüm: {plans[idx].plan_id}")
            fig_big = render_plan(plans[idx], figsize=(16, 12))
            st.pyplot(fig_big, use_container_width=True)
            plt.close(fig_big)

            st.markdown("**Oda Detayları:**")
            room_data = []
            for room in plans[idx].rooms:
                room_data.append({
                    "Oda": room.label.replace("\n", " - "),
                    "Net Alan (m²)": f"{room.area:.1f}",
                    "Genişlik (m)": f"{room.rect.w:.2f}",
                    "Uzunluk (m)": f"{room.rect.h:.2f}",
                    "Daire": f"Daire {room.apartment_id + 1}" if room.apartment_id >= 0 else "Ortak",
                })
            st.table(room_data)

            if st.button("✖️ Kapat"):
                del st.session_state["zoomed_plan"]
                st.rerun()

with st.sidebar:
    st.markdown("### Ayarlar")
    st.page_link("pages/admin.py", label="⚙️ Yapı Yönetmeliği Ayarları")
    st.divider()
    st.caption("Kat Planı Üretici v2.0")
    st.caption("AI kullanılmaz - Algoritmik plan üretimi")
    st.caption(f"Merdiven şaftı: {codes.stairs_width}m genişlik (tam kat yüksekliği) | "
               f"Asansör kuyusu: {codes.elevator_width}m genişlik (tam kat yüksekliği)")
    st.caption(f"Koridor: {codes.raw.get('building_corridor', {}).get('min_width', 1.5)}m | "
               f"PAİY Madde 29/31/34 uyumlu")
