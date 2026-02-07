"""
Mimari kalitede plan çizimi - v2.
Referans görsele uygun: kalın duvarlar, yay kapılar, şematik mobilya.
"""

from __future__ import annotations

import io
import math

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Arc, FancyBboxPatch, Circle
from matplotlib.figure import Figure
import numpy as np

from core.models import FloorPlan, PlacedRoom, RoomType, ROOM_DISPLAY_NAMES
from core.furniture import get_room_furniture, FurnitureItem


# ── Renk paleti (referans görsele uygun) ──────────────────────────────────────

ROOM_FILLS = {
    RoomType.SALON: "#FFFFFF",
    RoomType.YATAK_ODASI: "#FFFFFF",
    RoomType.ODA: "#FFFFFF",
    RoomType.MUTFAK: "#FFFFFF",
    RoomType.BANYO: "#E8EFF5",       # açık mavi (ıslak alan)
    RoomType.TUVALET: "#E8EFF5",
    RoomType.ANTRE: "#F5F5F5",
    RoomType.KORIDOR_DAIRE: "#F0F0F0",
    RoomType.KORIDOR_BINA: "#EDEDED",
    RoomType.MERDIVEN: "#E0E0E0",
    RoomType.ASANSOR: "#D8D8D8",
}

WALL_COLOR = "#333333"
OUTER_WALL_COLOR = "#222222"
FURNITURE_COLOR = "#666666"
FURNITURE_FILL = "#F8F8F8"
DOOR_COLOR = "#444444"
WINDOW_COLOR = "#4488CC"
LABEL_COLOR = "#333333"


def render_plan(
    plan: FloorPlan,
    figsize: tuple[float, float] = (14, 10),
    title: str | None = None,
) -> Figure:
    """FloorPlan'ı mimari kalitede matplotlib Figure olarak çiz."""
    fig, ax = plt.subplots(1, 1, figsize=figsize)
    br = plan.building_rect
    ow = 0.25  # dış duvar kalınlığı

    # Arka plan
    ax.set_facecolor("white")

    # 1. Dış duvarlar (kalın, koyu)
    _draw_thick_walls_outer(ax, br, ow)

    # 2. Odaları çiz (zemin rengi + ince çerçeve)
    for room in plan.rooms:
        fill = ROOM_FILLS.get(room.room_type, "#FFFFFF")
        room_patch = patches.Rectangle(
            (room.rect.x, room.rect.y), room.rect.w, room.rect.h,
            linewidth=0.8, edgecolor=WALL_COLOR, facecolor=fill, zorder=1,
        )
        ax.add_patch(room_patch)

    # 3. İç duvarlar (kalın çizgiler)
    _draw_inner_walls(ax, plan)

    # 4. Kapılar (yay gösterimi)
    for room in plan.rooms:
        for door in room.doors:
            _draw_door_arc(ax, room, door)

    # 5. Pencereler
    for room in plan.rooms:
        for window in room.windows:
            _draw_window(ax, room, window)

    # 6. Mobilyalar
    for room in plan.rooms:
        if room.room_type in (RoomType.KORIDOR_DAIRE, RoomType.KORIDOR_BINA,
                               RoomType.MERDIVEN, RoomType.ASANSOR, RoomType.ANTRE):
            if room.room_type == RoomType.MERDIVEN:
                _draw_stairs_symbol(ax, room.rect)
            elif room.room_type == RoomType.ASANSOR:
                _draw_elevator_symbol(ax, room.rect)
            continue

        furniture = get_room_furniture(room.room_type, room.rect.w, room.rect.h)
        for item in furniture:
            _draw_furniture(ax, room.rect, item)

    # 7. Etiketler
    for room in plan.rooms:
        _draw_label(ax, room)

    # 8. Giriş oku (bina koridoruna)
    _draw_entry_arrow(ax, plan)

    # 9. Ölçü bilgileri
    ax.text(br.cx, br.y - 1.2, f"{br.w:.1f} m",
            ha="center", fontsize=11, color="#444")
    ax.text(br.x - 1.2, br.cy, f"{br.h:.1f} m",
            ha="center", fontsize=11, color="#444", rotation=90)

    # Eksen ayarları
    margin = 2.0
    ax.set_xlim(br.x - margin, br.x2 + margin)
    ax.set_ylim(br.y - margin, br.y2 + margin)
    ax.set_aspect("equal")
    ax.axis("off")

    if title:
        ax.set_title(title, fontsize=14, fontweight="bold", pad=15)
    else:
        score_pct = plan.fitness_score * 100
        ax.set_title(f"{plan.plan_id}  (Skor: {score_pct:.0f}%)", fontsize=13, pad=12)

    fig.tight_layout()
    return fig


def render_plan_to_bytes(plan: FloorPlan, fmt: str = "png", **kwargs) -> bytes:
    fig = render_plan(plan, **kwargs)
    buf = io.BytesIO()
    fig.savefig(buf, format=fmt, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


# ── Duvarlar ──────────────────────────────────────────────────────────────────

def _draw_thick_walls_outer(ax, br, thickness: float):
    """Dış duvarları kalın dolgulu dikdörtgenler olarak çiz."""
    bx, by, bw, bh = br.x, br.y, br.w, br.h
    t = thickness

    # Alt duvar
    ax.add_patch(patches.Rectangle((bx, by), bw, t, fc=OUTER_WALL_COLOR, ec="none"))
    # Üst duvar
    ax.add_patch(patches.Rectangle((bx, by + bh - t), bw, t, fc=OUTER_WALL_COLOR, ec="none"))
    # Sol duvar
    ax.add_patch(patches.Rectangle((bx, by), t, bh, fc=OUTER_WALL_COLOR, ec="none"))
    # Sağ duvar
    ax.add_patch(patches.Rectangle((bx + bw - t, by), t, bh, fc=OUTER_WALL_COLOR, ec="none"))


def _draw_inner_walls(ax, plan: FloorPlan):
    """
    İç duvarları kalın dolgulu dikdörtgenler olarak çiz.
    Gap-aware: odalar arası iw boşluğunu da duvar olarak çizer.
    Daireler arası duvarlar daha kalın (taşıyıcı duvar).
    """
    drawn = set()
    rooms = plan.rooms
    br = plan.building_rect
    ow = 0.25  # dış duvar kalınlığı
    iw = 0.15  # iç duvar kalınlığı
    cw = 0.20  # taşıyıcı duvar (daireler arası / ortak alan sınırı)
    gap_tol = iw + 0.12  # Odalar arası bu mesafede ise duvar çiz

    for i, ra in enumerate(rooms):
        for j, rb in enumerate(rooms):
            if i >= j:
                continue
            key = (min(ra.room_id, rb.room_id), max(ra.room_id, rb.room_id))
            if key in drawn:
                continue

            a, b = ra.rect, rb.rect

            # Duvar kalınlığı: farklı daireler arası daha kalın
            diff_apt = (ra.apartment_id != rb.apartment_id
                        and ra.apartment_id >= 0 and rb.apartment_id >= 0)
            common_boundary = (ra.apartment_id == -1) != (rb.apartment_id == -1)
            thickness = cw if (diff_apt or common_boundary) else iw

            # --- Dikey duvar (odalar yan yana, x yönünde bitişik) ---

            # a'nın sağ kenarı ~ b'nin sol kenarı
            dx1 = b.x - a.x2
            if -0.05 <= dx1 < gap_tol:
                ys, ye = max(a.y, b.y), min(a.y2, b.y2)
                if ye - ys > 0.1:
                    cx = (a.x2 + b.x) / 2
                    drawn.add(key)
                    ax.add_patch(patches.Rectangle(
                        (cx - thickness / 2, ys), thickness, ye - ys,
                        fc=WALL_COLOR, ec="none", zorder=2,
                    ))
                    continue

            # b'nin sağ kenarı ~ a'nın sol kenarı
            dx2 = a.x - b.x2
            if -0.05 <= dx2 < gap_tol:
                ys, ye = max(a.y, b.y), min(a.y2, b.y2)
                if ye - ys > 0.1:
                    cx = (b.x2 + a.x) / 2
                    drawn.add(key)
                    ax.add_patch(patches.Rectangle(
                        (cx - thickness / 2, ys), thickness, ye - ys,
                        fc=WALL_COLOR, ec="none", zorder=2,
                    ))
                    continue

            # --- Yatay duvar (odalar üst üste, y yönünde bitişik) ---

            # a'nın üst kenarı ~ b'nin alt kenarı
            dy1 = b.y - a.y2
            if -0.05 <= dy1 < gap_tol:
                xs, xe = max(a.x, b.x), min(a.x2, b.x2)
                if xe - xs > 0.1:
                    cy = (a.y2 + b.y) / 2
                    drawn.add(key)
                    ax.add_patch(patches.Rectangle(
                        (xs, cy - thickness / 2), xe - xs, thickness,
                        fc=WALL_COLOR, ec="none", zorder=2,
                    ))
                    continue

            # b'nin üst kenarı ~ a'nın alt kenarı
            dy2 = a.y - b.y2
            if -0.05 <= dy2 < gap_tol:
                xs, xe = max(a.x, b.x), min(a.x2, b.x2)
                if xe - xs > 0.1:
                    cy = (b.y2 + a.y) / 2
                    drawn.add(key)
                    ax.add_patch(patches.Rectangle(
                        (xs, cy - thickness / 2), xe - xs, thickness,
                        fc=WALL_COLOR, ec="none", zorder=2,
                    ))

    # Oda kenar duvarları: bina iç sınırına değmeyen kenarlarda duvar çiz
    _draw_room_edge_walls(ax, rooms, br, ow, iw)


def _draw_room_edge_walls(ax, rooms, br, ow, iw):
    """
    Her odanın bina dış duvarına değmeyen kenarlarında duvar çiz.
    Bu, bitişik olmayan (komşu bulunamayan) kenarlar için yedek güvence sağlar.
    """
    tol = ow + 0.15  # Dış duvar + tolerans

    for room in rooms:
        r = room.rect
        if r.w < 0.3 or r.h < 0.3:
            continue

        # Her kenarın bina dış sınırına yakınlığını kontrol et
        near_south = (r.y - br.y) < tol
        near_north = (br.y2 - r.y2) < tol
        near_west = (r.x - br.x) < tol
        near_east = (br.x2 - r.x2) < tol

        # Güney kenar
        if not near_south:
            ax.add_patch(patches.Rectangle(
                (r.x, r.y - iw / 2), r.w, iw,
                fc=WALL_COLOR, ec="none", zorder=2, alpha=0.7,
            ))
        # Kuzey kenar
        if not near_north:
            ax.add_patch(patches.Rectangle(
                (r.x, r.y2 - iw / 2), r.w, iw,
                fc=WALL_COLOR, ec="none", zorder=2, alpha=0.7,
            ))
        # Batı kenar
        if not near_west:
            ax.add_patch(patches.Rectangle(
                (r.x - iw / 2, r.y), iw, r.h,
                fc=WALL_COLOR, ec="none", zorder=2, alpha=0.7,
            ))
        # Doğu kenar
        if not near_east:
            ax.add_patch(patches.Rectangle(
                (r.x2 - iw / 2, r.y), iw, r.h,
                fc=WALL_COLOR, ec="none", zorder=2, alpha=0.7,
            ))


# ── Kapılar (Yay gösterimi) ──────────────────────────────────────────────────

def _draw_door_arc(ax, room: PlacedRoom, door):
    """
    Kapıyı mimari standartta çiz: çeyrek daire yay + kapı yaprağı çizgisi.
    Referans görseldeki gibi açılma yönü gösterilir.
    """
    r = room.rect
    dw = door.width
    hw = dw / 2

    if door.wall_side == "east":
        # Kapı doğu duvarında, odanın içine açılır
        cx = r.x2
        cy = door.position
        # Duvar üzerinde boşluk (beyaz)
        ax.plot([cx, cx], [cy - hw, cy + hw], color="white", linewidth=4, zorder=5)
        # Kapı yaprağı (çizgi)
        ax.plot([cx, cx - dw], [cy - hw, cy - hw], color=DOOR_COLOR, linewidth=1.2, zorder=6)
        # Yay
        arc = Arc((cx, cy - hw), dw * 2, dw * 2, angle=0, theta1=90, theta2=180,
                  color=DOOR_COLOR, linewidth=0.8, linestyle="--", zorder=6)
        ax.add_patch(arc)

    elif door.wall_side == "west":
        cx = r.x
        cy = door.position
        ax.plot([cx, cx], [cy - hw, cy + hw], color="white", linewidth=4, zorder=5)
        ax.plot([cx, cx + dw], [cy - hw, cy - hw], color=DOOR_COLOR, linewidth=1.2, zorder=6)
        arc = Arc((cx, cy - hw), dw * 2, dw * 2, angle=0, theta1=0, theta2=90,
                  color=DOOR_COLOR, linewidth=0.8, linestyle="--", zorder=6)
        ax.add_patch(arc)

    elif door.wall_side == "north":
        cx = door.position
        cy = r.y2
        ax.plot([cx - hw, cx + hw], [cy, cy], color="white", linewidth=4, zorder=5)
        ax.plot([cx - hw, cx - hw], [cy, cy - dw], color=DOOR_COLOR, linewidth=1.2, zorder=6)
        arc = Arc((cx - hw, cy), dw * 2, dw * 2, angle=0, theta1=270, theta2=360,
                  color=DOOR_COLOR, linewidth=0.8, linestyle="--", zorder=6)
        ax.add_patch(arc)

    elif door.wall_side == "south":
        cx = door.position
        cy = r.y
        ax.plot([cx - hw, cx + hw], [cy, cy], color="white", linewidth=4, zorder=5)
        ax.plot([cx - hw, cx - hw], [cy, cy + dw], color=DOOR_COLOR, linewidth=1.2, zorder=6)
        arc = Arc((cx - hw, cy), dw * 2, dw * 2, angle=0, theta1=0, theta2=90,
                  color=DOOR_COLOR, linewidth=0.8, linestyle="--", zorder=6)
        ax.add_patch(arc)


# ── Pencereler ────────────────────────────────────────────────────────────────

def _draw_window(ax, room: PlacedRoom, window):
    """Pencereyi mimari standartta çiz (çift çizgi, dış duvarda)."""
    r = room.rect
    hw = window.width / 2
    gap = 0.08  # çift çizgi arası

    if window.wall_side in ("north", "south"):
        y = r.y2 if window.wall_side == "north" else r.y
        x1, x2 = window.position - hw, window.position + hw
        # Duvar üzerinde boşluk
        ax.plot([x1, x2], [y, y], color="white", linewidth=5, zorder=4)
        # Çift çizgi (cam)
        ax.plot([x1, x2], [y - gap, y - gap], color=WINDOW_COLOR, linewidth=1.5, zorder=5)
        ax.plot([x1, x2], [y + gap, y + gap], color=WINDOW_COLOR, linewidth=1.5, zorder=5)
        # Uç çizgiler
        ax.plot([x1, x1], [y - gap, y + gap], color=WINDOW_COLOR, linewidth=1.0, zorder=5)
        ax.plot([x2, x2], [y - gap, y + gap], color=WINDOW_COLOR, linewidth=1.0, zorder=5)
    else:
        x = r.x2 if window.wall_side == "east" else r.x
        y1, y2 = window.position - hw, window.position + hw
        ax.plot([x, x], [y1, y2], color="white", linewidth=5, zorder=4)
        ax.plot([x - gap, x - gap], [y1, y2], color=WINDOW_COLOR, linewidth=1.5, zorder=5)
        ax.plot([x + gap, x + gap], [y1, y2], color=WINDOW_COLOR, linewidth=1.5, zorder=5)
        ax.plot([x - gap, x + gap], [y1, y1], color=WINDOW_COLOR, linewidth=1.0, zorder=5)
        ax.plot([x - gap, x + gap], [y2, y2], color=WINDOW_COLOR, linewidth=1.0, zorder=5)


# ── Mobilya çizimi ────────────────────────────────────────────────────────────

def _draw_furniture(ax, room_rect: Rect, item: FurnitureItem):
    """Mobilya parçasını oda içinde çiz."""
    rx, ry = room_rect.x, room_rect.y
    fx = rx + item.x
    fy = ry + item.y
    fw, fh = item.width, item.height

    if item.shape == "circle":
        circle = Circle(
            (fx + fw / 2, fy + fh / 2), fw / 2,
            fc=FURNITURE_FILL, ec=FURNITURE_COLOR, linewidth=0.6, zorder=3,
        )
        ax.add_patch(circle)
    elif item.shape == "arc":
        # Yarım daire (lavabo gibi)
        arc_patch = Arc(
            (fx + fw / 2, fy), fw, fh * 2, angle=0, theta1=0, theta2=180,
            color=FURNITURE_COLOR, linewidth=0.7, zorder=3,
        )
        ax.add_patch(arc_patch)
        ax.plot([fx, fx + fw], [fy, fy], color=FURNITURE_COLOR, linewidth=0.7, zorder=3)
    else:
        # Dikdörtgen
        furn_patch = patches.Rectangle(
            (fx, fy), fw, fh,
            linewidth=0.6, edgecolor=FURNITURE_COLOR, facecolor=FURNITURE_FILL, zorder=3,
        )
        ax.add_patch(furn_patch)

        # Özel çizimler
        if "Yatak" in item.name:
            _draw_bed_detail(ax, fx, fy, fw, fh)
        elif "Klozet" in item.name:
            _draw_toilet_detail(ax, fx, fy, fw, fh)
        elif "Küvet" in item.name or "Duş" in item.name:
            _draw_bath_detail(ax, fx, fy, fw, fh)
        elif "Koltuk" in item.name:
            _draw_sofa_detail(ax, fx, fy, fw, fh)
        elif "Ocak" in item.name:
            _draw_stove_detail(ax, fx, fy, fw, fh)


def _draw_bed_detail(ax, x, y, w, h):
    """Yatak detayı: yastık."""
    pw = w * 0.35
    ph = 0.25
    # İki yastık üst kısımda
    py = y + h - ph - 0.1
    ax.add_patch(patches.FancyBboxPatch(
        (x + 0.1, py), pw, ph, boxstyle="round,pad=0.03",
        fc="#E8E8E8", ec=FURNITURE_COLOR, linewidth=0.4, zorder=4,
    ))
    ax.add_patch(patches.FancyBboxPatch(
        (x + w - pw - 0.1, py), pw, ph, boxstyle="round,pad=0.03",
        fc="#E8E8E8", ec=FURNITURE_COLOR, linewidth=0.4, zorder=4,
    ))


def _draw_toilet_detail(ax, x, y, w, h):
    """Klozet detayı: oval."""
    cx, cy = x + w / 2, y + h * 0.55
    ax.add_patch(patches.Ellipse(
        (cx, cy), w * 0.7, h * 0.55,
        fc="white", ec=FURNITURE_COLOR, linewidth=0.5, zorder=4,
    ))


def _draw_bath_detail(ax, x, y, w, h):
    """Küvet/duş detayı."""
    ax.add_patch(patches.FancyBboxPatch(
        (x + 0.05, y + 0.05), w - 0.10, h - 0.10,
        boxstyle="round,pad=0.05",
        fc="#EEF4F8", ec=FURNITURE_COLOR, linewidth=0.4, zorder=4,
    ))


def _draw_sofa_detail(ax, x, y, w, h):
    """Koltuk detayı: arka yaslanma."""
    back_h = h * 0.25
    ax.add_patch(patches.Rectangle(
        (x, y + h - back_h), w, back_h,
        fc="#E0E0E0", ec=FURNITURE_COLOR, linewidth=0.4, zorder=4,
    ))


def _draw_stove_detail(ax, x, y, w, h):
    """Ocak detayı: 4 daire."""
    r = min(w, h) * 0.18
    positions = [
        (x + w * 0.3, y + h * 0.3),
        (x + w * 0.7, y + h * 0.3),
        (x + w * 0.3, y + h * 0.7),
        (x + w * 0.7, y + h * 0.7),
    ]
    for px, py in positions:
        ax.add_patch(Circle((px, py), r, fc="none", ec=FURNITURE_COLOR, linewidth=0.5, zorder=4))


# ── Özel semboller ────────────────────────────────────────────────────────────

def _draw_stairs_symbol(ax, rect):
    """
    Merdiven sembolü: U-dönüş merdiven (iki kollu).
    Şaft tam kat yüksekliğini kaplar, basamaklar sadece ortadaki
    merdiven evi bölgesinde çizilir (config'den stairs_length kadar).
    """
    from core.building_codes import BuildingCodes
    codes = BuildingCodes()
    stair_flight_h = codes.stairs_length  # Merdiven evi uzunluğu (ör. 5.0m)

    # Merdiven basamaklarının çizileceği bölge (ortada)
    flight_cy = rect.cy
    flight_top = flight_cy + stair_flight_h / 2
    flight_bot = flight_cy - stair_flight_h / 2

    # Sınır kontrolü
    flight_top = min(flight_top, rect.y2 - 0.2)
    flight_bot = max(flight_bot, rect.y + 0.2)
    actual_h = flight_top - flight_bot

    if actual_h < 2.0:
        # Çok küçükse basit çizgiler
        n_steps = max(4, int(actual_h / 0.3))
        for i in range(n_steps):
            y = flight_bot + i * (actual_h / n_steps)
            ax.plot([rect.x + 0.15, rect.x2 - 0.15], [y, y],
                    color="#888", linewidth=0.5, zorder=3)
        return

    margin = 0.15
    mid_x = rect.cx
    arm_w = (rect.w - 2 * margin - 0.15) / 2  # İki kol arası 0.15m boşluk
    left_x1, left_x2 = rect.x + margin, rect.x + margin + arm_w
    right_x1, right_x2 = rect.x2 - margin - arm_w, rect.x2 - margin

    # Sol kol: aşağıdan yukarıya (çıkış)
    half_h = actual_h / 2
    landing_h = min(1.2, half_h * 0.25)
    flight_h = half_h - landing_h

    # Sol kol basamakları
    n_steps_arm = max(4, int(flight_h / 0.28))
    step_h = flight_h / n_steps_arm
    for i in range(n_steps_arm + 1):
        y = flight_bot + landing_h + i * step_h
        ax.plot([left_x1, left_x2], [y, y], color="#888", linewidth=0.5, zorder=3)
    # Sol kol yan çizgiler
    ax.plot([left_x1, left_x1], [flight_bot + landing_h, flight_bot + landing_h + flight_h],
            color="#888", linewidth=0.6, zorder=3)
    ax.plot([left_x2, left_x2], [flight_bot + landing_h, flight_bot + landing_h + flight_h],
            color="#888", linewidth=0.6, zorder=3)

    # Sağ kol basamakları (ters yön)
    for i in range(n_steps_arm + 1):
        y = flight_top - landing_h - i * step_h
        ax.plot([right_x1, right_x2], [y, y], color="#888", linewidth=0.5, zorder=3)
    # Sağ kol yan çizgiler
    ax.plot([right_x1, right_x1], [flight_top - landing_h - flight_h, flight_top - landing_h],
            color="#888", linewidth=0.6, zorder=3)
    ax.plot([right_x2, right_x2], [flight_top - landing_h - flight_h, flight_top - landing_h],
            color="#888", linewidth=0.6, zorder=3)

    # Alt sahanlık
    ax.plot([left_x1, right_x2], [flight_bot + landing_h, flight_bot + landing_h],
            color="#888", linewidth=0.6, zorder=3)
    ax.plot([left_x1, right_x2], [flight_bot, flight_bot],
            color="#888", linewidth=0.6, zorder=3)

    # Üst sahanlık
    ax.plot([left_x1, right_x2], [flight_top - landing_h, flight_top - landing_h],
            color="#888", linewidth=0.6, zorder=3)
    ax.plot([left_x1, right_x2], [flight_top, flight_top],
            color="#888", linewidth=0.6, zorder=3)

    # Yön oku (sol kolda yukarı)
    arrow_x = (left_x1 + left_x2) / 2
    ax.annotate("", xy=(arrow_x, flight_bot + landing_h + flight_h - 0.1),
                xytext=(arrow_x, flight_bot + landing_h + 0.3),
                arrowprops=dict(arrowstyle="->", color="#555", lw=1.0), zorder=4)

    # Ayırıcı çizgi (iki kol arası)
    ax.plot([mid_x, mid_x], [flight_bot + landing_h, flight_top - landing_h],
            color="#888", linewidth=0.4, linestyle="--", zorder=3)


def _draw_elevator_symbol(ax, rect):
    """
    Asansör sembolü: kuyu tam yüksekliktir, X sembolü sadece ortadaki
    kabin bölgesinde çizilir.
    """
    from core.building_codes import BuildingCodes
    codes = BuildingCodes()
    cabin_h = codes.elevator_length  # Kabin uzunluğu (ör. 2.5m)

    # Kabin bölgesi (ortada)
    cabin_cy = rect.cy
    cabin_top = min(cabin_cy + cabin_h / 2, rect.y2 - 0.1)
    cabin_bot = max(cabin_cy - cabin_h / 2, rect.y + 0.1)

    margin = 0.15

    # Kabin dikdörtgeni
    cx1, cy1 = rect.x + margin, cabin_bot
    cw = rect.w - 2 * margin
    ch = cabin_top - cabin_bot
    ax.add_patch(patches.Rectangle(
        (cx1, cy1), cw, ch,
        fc="#E8E8E8", ec="#888", linewidth=0.8, zorder=3,
    ))

    # X çapraz çizgiler (kabin içinde)
    ax.plot([cx1, cx1 + cw], [cy1, cy1 + ch], color="#888", linewidth=0.6, zorder=3)
    ax.plot([cx1, cx1 + cw], [cy1 + ch, cy1], color="#888", linewidth=0.6, zorder=3)

    # Kapı gösterimi (ortada ince çizgi)
    door_y = cabin_cy
    ax.plot([rect.x2 - 0.05, rect.x2 + 0.05], [door_y - 0.4, door_y - 0.4],
            color="#444", linewidth=1.5, zorder=4)
    ax.plot([rect.x2 - 0.05, rect.x2 + 0.05], [door_y + 0.4, door_y + 0.4],
            color="#444", linewidth=1.5, zorder=4)


def _draw_entry_arrow(ax, plan: FloorPlan):
    """Giriş okunu çiz."""
    for room in plan.rooms:
        if room.room_type == RoomType.KORIDOR_BINA:
            # Bina koridorunun ortasına giriş oku
            ax.annotate(
                "",
                xy=(room.rect.cx, room.rect.y),
                xytext=(room.rect.cx, room.rect.y - 1.0),
                arrowprops=dict(arrowstyle="-|>", color="#333", lw=2),
                zorder=10,
            )
            ax.text(room.rect.cx, room.rect.y - 1.3, "GİRİŞ",
                    ha="center", fontsize=9, fontweight="bold", color="#333")
            break


# ── Etiketler ─────────────────────────────────────────────────────────────────

def _draw_label(ax, room: PlacedRoom):
    """Oda etiketi: Ad + m²."""
    if room.rect.w < 0.5 or room.rect.h < 0.5:
        return

    name = ROOM_DISPLAY_NAMES.get(room.room_type, room.room_type.value)
    cx, cy = room.rect.cx, room.rect.cy
    font_size = max(5.5, min(9, room.rect.min_dim * 2.0))

    # Merdiven ve asansör şaft elemanları: alan gösterme, sadece isim
    # (şaft tüm kat yüksekliğini kaplar, alan yanıltıcı olur)
    is_shaft = room.room_type in (RoomType.MERDIVEN, RoomType.ASANSOR)

    ax.text(cx, cy + font_size * 0.012, name,
            ha="center", va="bottom", fontsize=font_size,
            fontweight="bold", color=LABEL_COLOR, zorder=8)
    if not is_shaft:
        ax.text(cx, cy - font_size * 0.012, f"{room.area:.1f} m²",
                ha="center", va="top", fontsize=font_size * 0.8,
                color="#666666", zorder=8)
