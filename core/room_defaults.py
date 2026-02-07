"""
Oda tiplerine göre varsayılan davranışlar ve alan hesaplamaları.
Kullanıcı oda alanı GİRMEZ - bu modül toplam alana göre oda alanlarını dağıtır.
"""

from __future__ import annotations

from .models import RoomType, Rect
from .building_codes import BuildingCodes


def compute_room_target_areas(
    room_types: list[RoomType],
    available_area: float,
    codes: BuildingCodes,
) -> list[float]:
    """
    Oda listesi ve toplam kullanılabilir alana göre her odanın hedef alanını hesapla.
    
    Strateji:
    1. Her oda tipinin minimum alanını al
    2. Kalan alanı preferred_area_ratio'ya göre dağıt
    3. Hiçbir oda minimum alanın altına düşmez
    """
    n = len(room_types)
    if n == 0:
        return []

    # 1. Minimum alanları topla
    min_areas = [codes.min_area(rt) for rt in room_types]
    total_min = sum(min_areas)

    if total_min >= available_area:
        # Alan yetmiyorsa minimum alanları orantılı küçült
        scale = available_area / total_min * 0.95  # %5 koridor payı
        return [ma * scale for ma in min_areas]

    # 2. Kalan alanı orantılı dağıt
    remaining = available_area - total_min
    ratios = [codes.preferred_area_ratio(rt) for rt in room_types]
    total_ratio = sum(ratios) or 1.0

    targets = []
    for i, rt in enumerate(room_types):
        bonus = remaining * (ratios[i] / total_ratio)
        targets.append(min_areas[i] + bonus)

    return targets


def get_room_priority(room_type: RoomType) -> int:
    """
    Oda yerleştirme önceliği (düşük = önce yerleştirilir).
    Büyük ve dış duvar gerektiren odalar önce.
    """
    priority_map = {
        RoomType.SALON: 1,
        RoomType.MUTFAK: 2,
        RoomType.YATAK_ODASI: 3,
        RoomType.ODA: 4,
        RoomType.BANYO: 5,
        RoomType.BANYO: 6,
        RoomType.TUVALET: 7,
        RoomType.ANTRE: 8,
        RoomType.KORIDOR_DAIRE: 9,
    }
    return priority_map.get(room_type, 10)


def make_room_id(room_type: RoomType, index: int) -> str:
    """Benzersiz oda ID'si: 'yatak_odasi_0', 'salon_0'."""
    return f"{room_type.value}_{index}"


def assign_room_ids(room_types: list[RoomType]) -> list[str]:
    """Oda listesine benzersiz ID'ler ata."""
    counts: dict[RoomType, int] = {}
    ids = []
    for rt in room_types:
        idx = counts.get(rt, 0)
        ids.append(make_room_id(rt, idx))
        counts[rt] = idx + 1
    return ids
