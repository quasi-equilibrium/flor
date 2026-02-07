"""
Daire iç düzeni: Koridor-Şerit (Corridor-Strip) yerleşim algoritması.

Strateji:
  - Daire koridoru giriş kapısından içeriye doğru uzanır
  - Odalar koridorun sol ve sağ yanında sıralanır
  - Her oda SADECE koridora kapı ile bağlanır
  - Odalar arası geçiş kapısı YOKTUR
  - Islak alanlar bir arada gruplanır

  +--------+---------+
  | Salon  | Yatak 1 |
  |        |         |
  +--------+---------+
  |KORİDOR | Banyo   |
  |(1.2m)  +---------+
  +--------+ WC      |
  | Mutfak |         |
  +--------+---------+
  | Antre  |
  +--------+
  (kapı -> bina koridoru)
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from .models import (
    Rect, RoomType, PlacedRoom, DoorPlacement, WindowPlacement,
)
from .building_codes import BuildingCodes


@dataclass
class ApartmentPlan:
    """Tek daire planı."""
    rooms: list[PlacedRoom]
    corridor: PlacedRoom
    entry: PlacedRoom  # Antre
    score: float = 0.0


def layout_apartment(
    zone: Rect,
    room_types: list[RoomType],
    building_rect: Rect,
    corridor_side: str,
    apartment_id: int,
    codes: BuildingCodes,
    variant: int = 0,
) -> ApartmentPlan:
    """
    Daire bölgesi içinde odaları yerleştir.

    zone: dairenin sınır dikdörtgeni
    corridor_side: bina koridorunun daire sınırına göre yönü ("north"/"south")
      - "north" ise giriş kapısı dairenin güney kenarında (koridora bakan)
      - "south" ise giriş kapısı dairenin kuzey kenarında
    """
    iw = codes.inner_wall  # iç duvar kalınlığı
    corr_w = codes.raw.get("apartment_corridor", {}).get("min_width", 1.20)

    # Daire iç boyutları (dış duvarlar building_layout'ta zaten hesaplandı)
    ax, ay = zone.x, zone.y
    aw, ah = zone.w, zone.h

    # Giriş yönüne göre düzenleme
    # Koridor dairenin uzun ekseni boyunca uzanır
    # "north" -> giriş güneyde, koridor aşağıdan yukarıya
    # "south" -> giriş kuzeyde, koridor yukarıdan aşağıya

    # Koridor ortada dikey olarak geçer
    # Sol ve sağ şeritler oluşur

    # Varyant'a göre koridor pozisyonu değiştir
    if variant % 3 == 0:
        corr_offset_ratio = 0.45  # Sola yakın
    elif variant % 3 == 1:
        corr_offset_ratio = 0.55  # Sağa yakın
    else:
        corr_offset_ratio = 0.50  # Ortada

    left_w = (aw - corr_w - iw * 2) * corr_offset_ratio
    right_w = aw - left_w - corr_w - iw * 2

    # Minimum genişlik kontrolü: her şerit en geniş odanın min_width'ini karşılamalı
    # Sol şerit: yaşam + ıslak, Sağ şerit: yatak odaları (henüz atanmamış, genel min kullan)
    min_room_w = 2.50  # PAİY yatak odası/oda minimum dar kenar
    if left_w < min_room_w:
        left_w = min_room_w
        right_w = aw - left_w - corr_w - iw * 2
    if right_w < min_room_w:
        right_w = min_room_w
        left_w = aw - right_w - corr_w - iw * 2

    corr_x = ax + left_w + iw
    left_x = ax
    right_x = corr_x + corr_w + iw

    # Oda sınıflandırma
    wet_types = {RoomType.BANYO, RoomType.TUVALET}
    living_types = {RoomType.SALON, RoomType.MUTFAK}
    bedroom_types = {RoomType.YATAK_ODASI, RoomType.ODA}

    wet_rooms = [rt for rt in room_types if rt in wet_types]
    living_rooms = [rt for rt in room_types if rt in living_types]
    bed_rooms = [rt for rt in room_types if rt in bedroom_types]

    # Varyant'a göre sıralama değiştir
    if variant % 2 == 1:
        living_rooms, bed_rooms = bed_rooms, living_rooms

    # Sol şerit: yaşam alanları + ıslak alanlar
    left_rooms_types = living_rooms + wet_rooms
    # Sağ şerit: yatak odaları
    right_rooms_types = bed_rooms

    # Eğer bir taraf çok kalabalıksa dengeleme
    while len(left_rooms_types) > len(right_rooms_types) + 2 and left_rooms_types:
        right_rooms_types.append(left_rooms_types.pop())
    while len(right_rooms_types) > len(left_rooms_types) + 2 and right_rooms_types:
        left_rooms_types.append(right_rooms_types.pop())

    # Antre alanı: giriş tarafında, koridorun başında
    antre_h = max(1.5, min(2.5, ah * 0.12))

    if corridor_side == "north":
        # Giriş güneyde
        entry_y = ay
        rooms_start_y = ay + antre_h + iw
    else:
        # Giriş kuzeyde
        entry_y = ay + ah - antre_h
        rooms_start_y = ay

    rooms_available_h = ah - antre_h - iw

    # Sol şerit odaları yerleştir
    placed_rooms: list[PlacedRoom] = []
    room_counter: dict[RoomType, int] = {}

    def _make_id(rt: RoomType) -> str:
        idx = room_counter.get(rt, 0)
        room_counter[rt] = idx + 1
        return f"{rt.value}_{idx}"

    def _place_strip(
        strip_rooms: list[RoomType],
        strip_x: float,
        strip_w: float,
        start_y: float,
        avail_h: float,
        going_up: bool,
    ) -> list[PlacedRoom]:
        """Şerit içinde odaları sırala (overflow korumalı, boşluk dolduran)."""
        if not strip_rooms:
            return []

        results = []
        n = len(strip_rooms)

        # Her odaya alan hesapla
        total_wall = iw * max(0, n - 1)
        usable_h = avail_h - total_wall
        if usable_h < 2.0:
            usable_h = avail_h  # Çok sıkışıksa duvar payını yoksay

        target_areas = []
        for rt in strip_rooms:
            min_a = codes.min_area(rt)
            ratio = codes.preferred_area_ratio(rt)
            target = max(min_a, usable_h * strip_w * ratio)
            target_areas.append(target)

        total_target = sum(target_areas)
        if total_target <= 0:
            total_target = 1

        # PAİY minimum yükseklikler (altına düşülemez)
        min_heights = []
        for i, rt in enumerate(strip_rooms):
            min_h_area = codes.min_area(rt) / strip_w if strip_w > 0 else 1.5
            min_h_width = codes.min_width(rt) if strip_w >= codes.min_width(rt) else 1.0
            min_heights.append(max(min_h_area, min_h_width))

        total_min = sum(min_heights) + total_wall

        if total_min > avail_h + 0.01:
            # Minimumlar bile sığmıyor - yine de minimumlarda kal (taşma kabul)
            room_heights = min_heights[:]
        else:
            # Minimum üstü alanı orantılı dağıt
            extra_space = avail_h - total_min
            target_extras = []
            for i, rt in enumerate(strip_rooms):
                desired = usable_h * (target_areas[i] / total_target)
                extra_for_room = max(0, desired - min_heights[i])
                target_extras.append(extra_for_room)

            total_target_extra = sum(target_extras)
            if total_target_extra > 0:
                extra_scale = min(1.0, extra_space / total_target_extra)
                room_heights = [
                    min_heights[i] + target_extras[i] * extra_scale
                    for i in range(n)
                ]
            else:
                # Tüm odalar zaten minimum boyutta, kalan alanı eşit dağıt
                room_heights = min_heights[:]
                if n > 0 and extra_space > 0:
                    per_room = extra_space / n
                    room_heights = [h + per_room for h in room_heights]

        # Son odayı kalan alana genişlet (boşluk bırakma)
        remaining = avail_h - (sum(room_heights) + total_wall)
        if remaining > 0.05 and room_heights:
            room_heights[-1] += remaining

        # Odaları yerleştir
        current_y = start_y
        for i, rt in enumerate(strip_rooms):
            room_h = room_heights[i]

            if not going_up:
                ry = current_y
                current_y += room_h + iw
            else:
                ry = start_y + avail_h - (current_y - start_y) - room_h
                current_y += room_h + iw

            # Sınır koruması: oda daire bölgesini aşmasın
            if not going_up:
                max_y2 = start_y + avail_h
                if ry + room_h > max_y2 + 0.01:
                    room_h = max(1.0, max_y2 - ry)
            else:
                if ry < start_y - 0.01:
                    excess = start_y - ry
                    ry = start_y
                    room_h = max(1.0, room_h - excess)

            # Net alan (duvar kalınlığı düşülmüş)
            net_area = max(0, (strip_w - iw) * (room_h - iw))

            room = PlacedRoom(
                room_type=rt,
                room_id=_make_id(rt),
                rect=Rect(x=strip_x, y=ry, w=strip_w, h=room_h),
                apartment_id=apartment_id,
                net_area=round(net_area, 1),
            )

            # Kapı: koridora açılır
            door_side = "east" if strip_x < corr_x else "west"
            door_y = ry + room_h / 2
            room.doors.append(DoorPlacement(
                wall_side=door_side,
                position=door_y,
                width=codes.door_width(rt),
                swing_inside=True,
                connects_to="koridor",
            ))

            # Pencere: dış duvara değiyorsa (dış duvar kalınlığı kadar tolerans)
            exterior = room.rect.touches_edge(building_rect, tol=0.5)
            if codes.needs_window(rt):
                for side, touching in exterior.items():
                    if touching and side != door_side:
                        if side in ("north", "south"):
                            pos = room.rect.cx
                        else:
                            pos = room.rect.cy
                        room.windows.append(WindowPlacement(
                            wall_side=side,
                            position=pos,
                            width=codes.raw.get("windows", {}).get("standard_width", 1.20),
                            height=codes.raw.get("windows", {}).get("standard_height", 1.20),
                        ))
                        break

            results.append(room)

        return results

    going_up = (corridor_side == "north")

    left_placed = _place_strip(
        left_rooms_types, left_x, left_w,
        rooms_start_y, rooms_available_h, going_up,
    )
    right_placed = _place_strip(
        right_rooms_types, right_x, right_w,
        rooms_start_y, rooms_available_h, going_up,
    )

    placed_rooms.extend(left_placed)
    placed_rooms.extend(right_placed)

    # Koridor
    corridor = PlacedRoom(
        room_type=RoomType.KORIDOR_DAIRE,
        room_id=f"koridor_daire_{apartment_id}",
        rect=Rect(x=corr_x, y=rooms_start_y, w=corr_w, h=rooms_available_h),
        apartment_id=apartment_id,
    )

    # Antre: daire genişliğinde (strip boşluklarını kapatır)
    # Giriş seviyesinde tüm daire genişliğini kaplar
    entry = PlacedRoom(
        room_type=RoomType.ANTRE,
        room_id=f"antre_{apartment_id}",
        rect=Rect(x=ax, y=entry_y, w=aw, h=antre_h),
        apartment_id=apartment_id,
        net_area=round(max(0, (aw - iw * 2) * (antre_h - iw)), 1),
    )

    # Giriş kapısı (bina koridoruna)
    door_side = "south" if corridor_side == "north" else "north"
    entry.doors.append(DoorPlacement(
        wall_side=door_side,
        position=entry.rect.cx,
        width=codes.door_width(RoomType.ANTRE),
        swing_inside=True,
        connects_to="bina_koridoru",
    ))

    # Skor hesapla
    score = _score_apartment(placed_rooms, building_rect, codes)

    return ApartmentPlan(
        rooms=placed_rooms,
        corridor=corridor,
        entry=entry,
        score=score,
    )


def _score_apartment(
    rooms: list[PlacedRoom],
    building_rect: Rect,
    codes: BuildingCodes,
) -> float:
    """Daire düzeni kalite skoru."""
    if not rooms:
        return 0.0

    score = 0.5  # Başlangıç

    # Dış duvar erişimi
    exterior_need = 0
    exterior_have = 0
    for r in rooms:
        if codes.needs_exterior_wall(r.room_type):
            exterior_need += 1
            touches = r.rect.touches_edge(building_rect, tol=0.1)
            if any(touches.values()):
                exterior_have += 1

    if exterior_need > 0:
        score += 0.3 * (exterior_have / exterior_need)

    # Min alan uyumu
    area_ok = 0
    area_total = 0
    for r in rooms:
        min_a = codes.min_area(r.room_type)
        if min_a > 0:
            area_total += 1
            if r.area >= min_a * 0.85:
                area_ok += 1
    if area_total > 0:
        score += 0.2 * (area_ok / area_total)

    return min(1.0, score)


def generate_apartment_variants(
    zone: Rect,
    room_types: list[RoomType],
    building_rect: Rect,
    corridor_side: str,
    apartment_id: int,
    codes: BuildingCodes,
    n_variants: int = 8,
) -> list[ApartmentPlan]:
    """Birden fazla daire düzeni varyantı üret."""
    variants = []
    for v in range(n_variants):
        plan = layout_apartment(
            zone, room_types, building_rect,
            corridor_side, apartment_id, codes, variant=v,
        )
        variants.append(plan)

    variants.sort(key=lambda p: p.score, reverse=True)
    return variants
