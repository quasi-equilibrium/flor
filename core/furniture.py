"""
Mobilya tanımları ve otomatik yerleştirme.
Her oda tipine uygun şematik mobilyalar standart boyutlarda.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .models import Rect, RoomType


@dataclass
class FurnitureItem:
    """Tek mobilya parçası."""
    name: str
    width: float   # metre
    height: float  # metre (plandaki uzunluk)
    x: float = 0   # yerleşim x
    y: float = 0   # yerleşim y
    rotation: int = 0  # 0, 90, 180, 270 derece
    shape: str = "rect"  # "rect", "circle", "L", "arc"


# ── Standart Mobilya Boyutları ────────────────────────────────────────────────

# Yatak odası
DOUBLE_BED = FurnitureItem("Çift Kişilik Yatak", 1.60, 2.00)
SINGLE_BED = FurnitureItem("Tek Kişilik Yatak", 0.90, 2.00)
NIGHTSTAND = FurnitureItem("Komodin", 0.45, 0.45)
WARDROBE = FurnitureItem("Dolap", 0.60, 1.80)

# Salon
SOFA_3SEAT = FurnitureItem("3'lü Koltuk", 2.10, 0.85)
SOFA_2SEAT = FurnitureItem("2'li Koltuk", 1.50, 0.85)
COFFEE_TABLE = FurnitureItem("Sehpa", 1.10, 0.55)
TV_UNIT = FurnitureItem("TV Ünitesi", 1.60, 0.40)
DINING_TABLE_4 = FurnitureItem("Yemek Masası (4)", 1.20, 0.80)
DINING_TABLE_6 = FurnitureItem("Yemek Masası (6)", 1.60, 0.90)
CHAIR = FurnitureItem("Sandalye", 0.42, 0.42)

# Mutfak
KITCHEN_COUNTER = FurnitureItem("Tezgah", 0.60, 2.40)
KITCHEN_SINK = FurnitureItem("Evye", 0.60, 0.50)
STOVE = FurnitureItem("Ocak", 0.60, 0.60)
FRIDGE = FurnitureItem("Buzdolabı", 0.65, 0.70)

# Banyo
BATHTUB = FurnitureItem("Küvet", 0.75, 1.70)
SHOWER = FurnitureItem("Duşakabin", 0.90, 0.90)
BATH_SINK = FurnitureItem("Lavabo", 0.50, 0.40, shape="arc")
TOILET = FurnitureItem("Klozet", 0.40, 0.65)
WASHING_MACHINE = FurnitureItem("Çamaşır Mak.", 0.60, 0.60)

# WC
WC_TOILET = FurnitureItem("Klozet", 0.38, 0.55)
WC_SINK = FurnitureItem("Lavabo", 0.35, 0.30, shape="arc")

# Genel
DESK = FurnitureItem("Çalışma Masası", 1.20, 0.60)
DESK_CHAIR = FurnitureItem("Sandalye", 0.45, 0.45, shape="circle")


def get_room_furniture(room_type: RoomType, room_w: float, room_h: float) -> list[FurnitureItem]:
    """
    Oda tipine ve boyutuna göre mobilya listesi döndür.
    Mobilyalar odanın sol-alt köşesine göre koordinatlarla yerleştirilir.
    """
    margin = 0.15  # Duvardan boşluk
    items: list[FurnitureItem] = []

    if room_type == RoomType.YATAK_ODASI:
        items = _layout_bedroom(room_w, room_h, margin)
    elif room_type == RoomType.ODA:
        items = _layout_room(room_w, room_h, margin)
    elif room_type == RoomType.SALON:
        items = _layout_living(room_w, room_h, margin)
    elif room_type == RoomType.MUTFAK:
        items = _layout_kitchen(room_w, room_h, margin)
    elif room_type == RoomType.BANYO:
        items = _layout_bathroom(room_w, room_h, margin)
    elif room_type == RoomType.TUVALET:
        items = _layout_wc(room_w, room_h, margin)

    return items


def _layout_bedroom(w: float, h: float, m: float) -> list[FurnitureItem]:
    """Yatak odası mobilyaları."""
    items = []
    bed = FurnitureItem("Yatak", 1.60, 2.00)

    if w >= 3.0 and h >= 3.0:
        # Yatak üst duvara yaslanmış, ortada
        bed.x = (w - bed.width) / 2
        bed.y = h - bed.height - m
        items.append(bed)

        # Komodinler yatağın iki yanında
        ns1 = FurnitureItem("Komodin", 0.45, 0.45)
        ns1.x = bed.x - ns1.width - 0.05
        ns1.y = bed.y + bed.height - ns1.height
        if ns1.x >= m:
            items.append(ns1)

        ns2 = FurnitureItem("Komodin", 0.45, 0.45)
        ns2.x = bed.x + bed.width + 0.05
        ns2.y = bed.y + bed.height - ns2.height
        if ns2.x + ns2.width <= w - m:
            items.append(ns2)

        # Dolap karşı duvarda
        wardrobe = FurnitureItem("Dolap", min(1.80, w * 0.4), 0.60)
        wardrobe.x = m
        wardrobe.y = m
        items.append(wardrobe)
    else:
        # Küçük oda: tek kişilik yatak
        bed = FurnitureItem("Yatak", 0.90, 2.00)
        bed.x = m
        bed.y = h - bed.height - m
        items.append(bed)

    return items


def _layout_room(w: float, h: float, m: float) -> list[FurnitureItem]:
    """Genel oda (çalışma odası vb.)."""
    items = []
    # Çalışma masası
    desk = FurnitureItem("Masa", min(1.20, w * 0.5), 0.60)
    desk.x = m
    desk.y = h - desk.height - m
    items.append(desk)

    # Sandalye
    chair = FurnitureItem("Sandalye", 0.45, 0.45, shape="circle")
    chair.x = desk.x + desk.width / 2 - chair.width / 2
    chair.y = desk.y - chair.height - 0.2
    items.append(chair)

    # Tek yatak veya koltuk
    if h > 3.5:
        bed = FurnitureItem("Yatak", 0.90, 2.00)
        bed.x = w - bed.width - m
        bed.y = m
        items.append(bed)

    return items


def _layout_living(w: float, h: float, m: float) -> list[FurnitureItem]:
    """Salon mobilyaları."""
    items = []

    # Koltuk grubu
    sofa = FurnitureItem("Koltuk", min(2.10, w * 0.5), 0.85)
    sofa.x = m
    sofa.y = h - sofa.height - m
    items.append(sofa)

    # Sehpa
    table = FurnitureItem("Sehpa", 1.10, 0.55)
    table.x = sofa.x + (sofa.width - table.width) / 2
    table.y = sofa.y - table.height - 0.5
    if table.y > m:
        items.append(table)

    # TV ünitesi karşıda
    tv = FurnitureItem("TV", min(1.60, w * 0.4), 0.40)
    tv.x = sofa.x + (sofa.width - tv.width) / 2
    tv.y = m
    items.append(tv)

    # Yemek masası (eğer alan yetiyorsa)
    if w > 4.5:
        dtable = FurnitureItem("Yemek Masası", 1.20, 0.80)
        dtable.x = w - dtable.width - m
        dtable.y = h - dtable.height - m - 0.3
        items.append(dtable)

        # Sandalyeler
        for i in range(4):
            ch = FurnitureItem("Sandalye", 0.38, 0.38)
            if i < 2:
                ch.x = dtable.x + 0.15 + i * 0.55
                ch.y = dtable.y - ch.height - 0.05
            else:
                ch.x = dtable.x + 0.15 + (i - 2) * 0.55
                ch.y = dtable.y + dtable.height + 0.05
            items.append(ch)

    return items


def _layout_kitchen(w: float, h: float, m: float) -> list[FurnitureItem]:
    """Mutfak mobilyaları (L tezgah)."""
    items = []
    counter_depth = 0.60

    # Alt tezgah (sol duvar boyunca)
    counter_len = min(h - 2 * m, h * 0.7)
    counter = FurnitureItem("Tezgah", counter_depth, counter_len)
    counter.x = m
    counter.y = h - counter_len - m
    items.append(counter)

    # Üst tezgah (üst duvar boyunca)
    top_len = min(w - counter_depth - 2 * m, w * 0.5)
    if top_len > 0.5:
        top_counter = FurnitureItem("Tezgah", top_len, counter_depth)
        top_counter.x = counter.x + counter_depth
        top_counter.y = h - counter_depth - m
        items.append(top_counter)

    # Buzdolabı
    fridge = FurnitureItem("Buzdolabı", 0.65, 0.70)
    fridge.x = w - fridge.width - m
    fridge.y = h - fridge.height - m
    items.append(fridge)

    # Ocak (tezgah üzerinde simge)
    stove = FurnitureItem("Ocak", 0.55, 0.55, shape="circle")
    stove.x = counter.x + 0.03
    stove.y = counter.y + counter_len * 0.4
    items.append(stove)

    # Evye (tezgah üzerinde simge)
    sink = FurnitureItem("Evye", 0.45, 0.40, shape="arc")
    sink.x = counter.x + 0.08
    sink.y = counter.y + counter_len * 0.7
    items.append(sink)

    return items


def _layout_bathroom(w: float, h: float, m: float) -> list[FurnitureItem]:
    """Banyo mobilyaları."""
    items = []

    # Duş/küvet
    if w >= 2.5 and h >= 2.5:
        tub = FurnitureItem("Küvet", 0.75, 1.70)
        tub.x = m
        tub.y = h - tub.height - m
        items.append(tub)
    else:
        shower = FurnitureItem("Duş", 0.85, 0.85)
        shower.x = m
        shower.y = h - shower.height - m
        items.append(shower)

    # Lavabo
    sink = FurnitureItem("Lavabo", 0.50, 0.40, shape="arc")
    sink.x = w - sink.width - m
    sink.y = h - sink.height - m
    items.append(sink)

    # Klozet
    toilet = FurnitureItem("Klozet", 0.40, 0.65)
    toilet.x = w - toilet.width - m
    toilet.y = m
    items.append(toilet)

    # Çamaşır makinesi (eğer alan yetiyorsa)
    if w > 2.2 and h > 2.5:
        wm = FurnitureItem("Çam.Mak.", 0.60, 0.60)
        wm.x = m
        wm.y = m
        items.append(wm)

    return items


def _layout_wc(w: float, h: float, m: float) -> list[FurnitureItem]:
    """WC mobilyaları."""
    items = []

    # Klozet
    toilet = FurnitureItem("Klozet", 0.38, 0.55)
    toilet.x = (w - toilet.width) / 2
    toilet.y = m
    items.append(toilet)

    # Küçük lavabo
    sink = FurnitureItem("Lavabo", 0.35, 0.30, shape="arc")
    sink.x = (w - sink.width) / 2
    sink.y = h - sink.height - m
    items.append(sink)

    return items
