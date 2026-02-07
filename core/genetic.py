"""
Plan üretim motoru v2.
Bina düzeni + daire yerleşimi + 4 alternatif seçimi.
"""

from __future__ import annotations

from .models import (
    BuildingInput, RoomCountInput, RoomType, Rect,
    PlacedRoom, FloorPlan, WallSegment, Point,
)
from .building_codes import BuildingCodes
from .building_layout import compute_building_layout
from .apartment_layout import generate_apartment_variants


def generate_plans(
    building: BuildingInput,
    room_counts: RoomCountInput,
    codes: BuildingCodes,
    n_alternatives: int = 4,
) -> list[FloorPlan]:
    """
    Ana giriş noktası: 4 alternatif kat planı üret.

    Akış:
    1. Bina düzenini hesapla (çekirdek + koridor + daire bölgeleri)
    2. Her daire bölgesi için oda yerleşimi üret
    3. Farklı varyantları birleştirerek 4 alternatif oluştur
    4. Duvarları ve doğrulamayı ekle
    """
    room_types = room_counts.to_room_list()

    # 1. Bina düzeni
    zones = compute_building_layout(building, codes)

    # 2. Her daire için varyantlar üret
    all_apt_variants: list[list] = []  # [daire_idx][varyant_idx]
    for apt_idx, (zone, side) in enumerate(
        zip(zones.apartment_zones, zones.apartment_corridor_sides)
    ):
        variants = generate_apartment_variants(
            zone=zone,
            room_types=room_types,
            building_rect=zones.building_rect,
            corridor_side=side,
            apartment_id=apt_idx,
            codes=codes,
            n_variants=max(4, n_alternatives * 2),
        )
        all_apt_variants.append(variants)

    # 3. Varyant kombinasyonlarından alternatif planlar oluştur
    plans: list[FloorPlan] = []

    for alt_idx in range(n_alternatives):
        plan_rooms: list[PlacedRoom] = []
        total_score = 0.0

        # Ortak alanlar
        plan_rooms.append(PlacedRoom(
            room_type=RoomType.MERDIVEN,
            room_id="merdiven_0",
            rect=zones.stairs_rect,
            apartment_id=-1,
        ))

        if zones.elevator_rect:
            plan_rooms.append(PlacedRoom(
                room_type=RoomType.ASANSOR,
                room_id="asansor_0",
                rect=zones.elevator_rect,
                apartment_id=-1,
            ))

        if zones.elevator_rect_2:
            plan_rooms.append(PlacedRoom(
                room_type=RoomType.ASANSOR,
                room_id="asansor_1",
                rect=zones.elevator_rect_2,
                apartment_id=-1,
            ))

        plan_rooms.append(PlacedRoom(
            room_type=RoomType.KORIDOR_BINA,
            room_id="koridor_bina_0",
            rect=zones.corridor_rect,
            apartment_id=-1,
        ))

        # Her daire için varyant seç
        for apt_idx, variants in enumerate(all_apt_variants):
            v_idx = alt_idx % len(variants)
            apt_plan = variants[v_idx]

            plan_rooms.extend(apt_plan.rooms)
            plan_rooms.append(apt_plan.corridor)
            plan_rooms.append(apt_plan.entry)
            total_score += apt_plan.score

        avg_score = total_score / max(1, len(all_apt_variants))

        # Duvarları oluştur
        walls = _generate_walls(plan_rooms, zones.building_rect, codes)

        plan = FloorPlan(
            plan_id=f"alternatif_{alt_idx + 1}",
            building_rect=zones.building_rect,
            rooms=plan_rooms,
            walls=walls,
            fitness_score=avg_score,
            apartments_per_floor=building.apartments_per_floor,
        )

        plans.append(plan)

    return plans


def _generate_walls(
    rooms: list[PlacedRoom],
    building_rect: Rect,
    codes: BuildingCodes,
) -> list[WallSegment]:
    """Tüm duvar segmentlerini oluştur."""
    walls: list[WallSegment] = []
    ow = codes.outer_wall
    iw = codes.inner_wall

    # Dış duvarlar
    bx, by = building_rect.x, building_rect.y
    bx2, by2 = building_rect.x2, building_rect.y2

    walls.append(WallSegment(start=Point(x=bx, y=by), end=Point(x=bx2, y=by), thickness=ow, is_exterior=True))
    walls.append(WallSegment(start=Point(x=bx, y=by2), end=Point(x=bx2, y=by2), thickness=ow, is_exterior=True))
    walls.append(WallSegment(start=Point(x=bx, y=by), end=Point(x=bx, y=by2), thickness=ow, is_exterior=True))
    walls.append(WallSegment(start=Point(x=bx2, y=by), end=Point(x=bx2, y=by2), thickness=ow, is_exterior=True))

    # İç duvarlar: odalar arası paylaşılan kenarlar
    processed = set()
    for i, ra in enumerate(rooms):
        for j, rb in enumerate(rooms):
            if i >= j:
                continue
            key = (min(ra.room_id, rb.room_id), max(ra.room_id, rb.room_id))
            if key in processed:
                continue

            shared = ra.rect.shared_edge_length(rb.rect, tol=0.05)
            if shared < 0.1:
                continue

            processed.add(key)
            wall = _find_shared_wall(ra.rect, rb.rect, iw)
            if wall:
                walls.append(wall)

    return walls


def _find_shared_wall(a: Rect, b: Rect, thickness: float) -> WallSegment | None:
    tol = 0.05
    if abs(a.x2 - b.x) < tol:
        ys, ye = max(a.y, b.y), min(a.y2, b.y2)
        if ye > ys:
            return WallSegment(start=Point(x=a.x2, y=ys), end=Point(x=a.x2, y=ye), thickness=thickness)
    if abs(b.x2 - a.x) < tol:
        ys, ye = max(a.y, b.y), min(a.y2, b.y2)
        if ye > ys:
            return WallSegment(start=Point(x=a.x, y=ys), end=Point(x=a.x, y=ye), thickness=thickness)
    if abs(a.y2 - b.y) < tol:
        xs, xe = max(a.x, b.x), min(a.x2, b.x2)
        if xe > xs:
            return WallSegment(start=Point(x=xs, y=a.y2), end=Point(x=xe, y=a.y2), thickness=thickness)
    if abs(b.y2 - a.y) < tol:
        xs, xe = max(a.x, b.x), min(a.x2, b.x2)
        if xe > xs:
            return WallSegment(start=Point(x=xs, y=a.y), end=Point(x=xe, y=a.y), thickness=thickness)
    return None
