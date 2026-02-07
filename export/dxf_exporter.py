"""
Adım 10: DXF dışa aktarma.
ezdxf ile AutoCAD/LibreCAD uyumlu DXF dosyası üretir.
Katmanlar: ROOMS, WALLS, DOORS, WINDOWS, LABELS, DIMENSIONS
"""

from __future__ import annotations

import io
from pathlib import Path

import ezdxf
from ezdxf.enums import TextEntityAlignment

from core.models import FloorPlan, PlacedRoom, RoomType, WallSegment


# Oda tiplerine göre renkler (AutoCAD ACI renk indeksleri)
ROOM_COLORS = {
    RoomType.SALON: 3,           # yeşil
    RoomType.YATAK_ODASI: 5,     # mavi
    RoomType.ODA: 4,             # cyan
    RoomType.MUTFAK: 1,          # kırmızı
    RoomType.BANYO: 6,           # magenta
    RoomType.TUVALET: 6,         # magenta
    RoomType.ANTRE: 8,           # gri
    RoomType.KORIDOR_DAIRE: 8,   # gri
    RoomType.KORIDOR_BINA: 8,    # gri
    RoomType.MERDIVEN: 9,        # açık gri
    RoomType.ASANSOR: 9,         # açık gri
}


def export_to_dxf(plan: FloorPlan, filepath: str | Path | None = None) -> bytes | None:
    """
    FloorPlan'ı DXF dosyasına aktar.
    filepath verilirse dosyaya yazar, verilmezse bytes döndürür.
    """
    doc = ezdxf.new("R2013")
    msp = doc.modelspace()

    # Katmanları oluştur
    doc.layers.add("BUILDING", color=7)       # beyaz
    doc.layers.add("ROOMS", color=3)          # yeşil
    doc.layers.add("WALLS", color=7)          # beyaz
    doc.layers.add("DOORS", color=1)          # kırmızı
    doc.layers.add("WINDOWS", color=5)        # mavi
    doc.layers.add("LABELS", color=7)         # beyaz
    doc.layers.add("DIMENSIONS", color=2)     # sarı

    # Bina dış sınırı
    br = plan.building_rect
    _draw_rect(msp, br.x, br.y, br.w, br.h, "BUILDING", color=7)

    # Odalar
    for room in plan.rooms:
        color = ROOM_COLORS.get(room.room_type, 7)
        _draw_rect(msp, room.rect.x, room.rect.y, room.rect.w, room.rect.h, "ROOMS", color=color)

        # Etiket
        _draw_label(msp, room, "LABELS")

        # Kapılar
        for door in room.doors:
            _draw_door(msp, room, door, "DOORS")

        # Pencereler
        for window in room.windows:
            _draw_window(msp, room, window, "WINDOWS")

    # Duvarlar
    for wall in plan.walls:
        _draw_wall(msp, wall, "WALLS")

    # Ölçü çizgileri (bina dış kenarlar)
    _draw_dimensions(msp, plan, "DIMENSIONS")

    if filepath:
        doc.saveas(str(filepath))
        return None
    else:
        stream = io.StringIO()
        doc.write(stream)
        return stream.getvalue().encode("utf-8")


def _draw_rect(msp, x: float, y: float, w: float, h: float, layer: str, color: int = 7):
    """Dikdörtgen çiz."""
    points = [(x, y), (x + w, y), (x + w, y + h), (x, y + h), (x, y)]
    msp.add_lwpolyline(points, dxfattribs={"layer": layer, "color": color})


def _draw_label(msp, room: PlacedRoom, layer: str):
    """Oda etiketi (ad + m²)."""
    display_names = {
        RoomType.SALON: "Salon",
        RoomType.YATAK_ODASI: "Yatak Odası",
        RoomType.ODA: "Oda",
        RoomType.MUTFAK: "Mutfak",
        RoomType.BANYO: "Banyo",
        RoomType.TUVALET: "WC",
        RoomType.ANTRE: "Antre",
        RoomType.KORIDOR_DAIRE: "Koridor",
        RoomType.KORIDOR_BINA: "Koridor",
        RoomType.MERDIVEN: "Merdiven",
        RoomType.ASANSOR: "Asansör",
    }
    name = display_names.get(room.room_type, room.room_type.value)

    # İlk satır: oda adı
    text_height = min(0.3, room.rect.min_dim * 0.15)
    cx, cy = room.rect.cx, room.rect.cy

    msp.add_text(
        name,
        height=text_height,
        dxfattribs={"layer": layer, "color": 7},
    ).set_placement((cx, cy + text_height * 0.6), align=TextEntityAlignment.MIDDLE_CENTER)

    # İkinci satır: alan
    msp.add_text(
        f"{room.area:.1f} m²",
        height=text_height * 0.8,
        dxfattribs={"layer": layer, "color": 7},
    ).set_placement((cx, cy - text_height * 0.6), align=TextEntityAlignment.MIDDLE_CENTER)


def _draw_door(msp, room: PlacedRoom, door, layer: str):
    """Kapıyı çiz (basit açıklık)."""
    r = room.rect
    hw = door.width / 2

    if door.wall_side == "north":
        x1 = door.position - hw
        msp.add_line((x1, r.y2), (x1 + door.width, r.y2), dxfattribs={"layer": layer, "color": 1})
    elif door.wall_side == "south":
        x1 = door.position - hw
        msp.add_line((x1, r.y), (x1 + door.width, r.y), dxfattribs={"layer": layer, "color": 1})
    elif door.wall_side == "east":
        y1 = door.position - hw
        msp.add_line((r.x2, y1), (r.x2, y1 + door.width), dxfattribs={"layer": layer, "color": 1})
    elif door.wall_side == "west":
        y1 = door.position - hw
        msp.add_line((r.x, y1), (r.x, y1 + door.width), dxfattribs={"layer": layer, "color": 1})


def _draw_window(msp, room: PlacedRoom, window, layer: str):
    """Pencereyi çiz (dış duvarda çizgi)."""
    r = room.rect
    hw = window.width / 2

    if window.wall_side == "north":
        x1 = window.position - hw
        y = r.y2
        msp.add_line((x1, y - 0.05), (x1 + window.width, y - 0.05), dxfattribs={"layer": layer, "color": 5})
        msp.add_line((x1, y + 0.05), (x1 + window.width, y + 0.05), dxfattribs={"layer": layer, "color": 5})
    elif window.wall_side == "south":
        x1 = window.position - hw
        y = r.y
        msp.add_line((x1, y - 0.05), (x1 + window.width, y - 0.05), dxfattribs={"layer": layer, "color": 5})
        msp.add_line((x1, y + 0.05), (x1 + window.width, y + 0.05), dxfattribs={"layer": layer, "color": 5})
    elif window.wall_side == "east":
        y1 = window.position - hw
        x = r.x2
        msp.add_line((x - 0.05, y1), (x - 0.05, y1 + window.width), dxfattribs={"layer": layer, "color": 5})
        msp.add_line((x + 0.05, y1), (x + 0.05, y1 + window.width), dxfattribs={"layer": layer, "color": 5})
    elif window.wall_side == "west":
        y1 = window.position - hw
        x = r.x
        msp.add_line((x - 0.05, y1), (x - 0.05, y1 + window.width), dxfattribs={"layer": layer, "color": 5})
        msp.add_line((x + 0.05, y1), (x + 0.05, y1 + window.width), dxfattribs={"layer": layer, "color": 5})


def _draw_wall(msp, wall: WallSegment, layer: str):
    """Duvar segmentini çiz."""
    color = 7 if wall.is_exterior else 8
    msp.add_line(
        (wall.start.x, wall.start.y),
        (wall.end.x, wall.end.y),
        dxfattribs={"layer": layer, "color": color, "lineweight": 50 if wall.is_exterior else 25},
    )


def _draw_dimensions(msp, plan: FloorPlan, layer: str):
    """Bina dış kenar ölçülerini çiz."""
    br = plan.building_rect
    offset = 1.0  # Ölçü çizgisi bina dışında

    # Alt kenar ölçüsü
    msp.add_aligned_dim(
        p1=(br.x, br.y - offset),
        p2=(br.x2, br.y - offset),
        distance=0.5,
        dxfattribs={"layer": layer},
    ).render()

    # Sol kenar ölçüsü
    msp.add_aligned_dim(
        p1=(br.x - offset, br.y),
        p2=(br.x - offset, br.y2),
        distance=0.5,
        dxfattribs={"layer": layer},
    ).render()
