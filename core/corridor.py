"""
Adım 7: Koridor üretimi ve oda erişim bağlantıları.
MVP'de basit yaklaşım: koridor odası zaten slicing tree'de var,
ek olarak erişilebilirlik kontrolü yapar.
"""

from __future__ import annotations

from .models import Rect, RoomType, PlacedRoom
from .building_codes import BuildingCodes


def check_connectivity(rooms: list[PlacedRoom], tolerance: float = 0.05) -> dict[str, bool]:
    """
    Her odanın en az bir komşuya (koridor dahil) bağlı olup olmadığını kontrol et.
    Bağlantı = paylaşılan kenar uzunluğu > kapı genişliği.
    """
    result: dict[str, bool] = {}

    for room in rooms:
        if room.room_type in (RoomType.MERDIVEN, RoomType.ASANSOR):
            result[room.room_id] = True
            continue

        connected = False
        for other in rooms:
            if other.room_id == room.room_id:
                continue
            shared = room.rect.shared_edge_length(other.rect, tolerance)
            if shared >= 0.7:  # En az kapı genişliği kadar paylaşılan kenar
                connected = True
                break

        result[room.room_id] = connected

    return result


def find_neighbors(rooms: list[PlacedRoom], tolerance: float = 0.05) -> dict[str, list[str]]:
    """Her oda için komşu odaların listesi."""
    neighbors: dict[str, list[str]] = {r.room_id: [] for r in rooms}

    for i, room_a in enumerate(rooms):
        for j, room_b in enumerate(rooms):
            if i >= j:
                continue
            shared = room_a.rect.shared_edge_length(room_b.rect, tolerance)
            if shared >= 0.3:  # Minimum temas
                neighbors[room_a.room_id].append(room_b.room_id)
                neighbors[room_b.room_id].append(room_a.room_id)

    return neighbors


def compute_corridor_quality(rooms: list[PlacedRoom]) -> float:
    """
    Koridor kalitesi skoru (0-1).
    - Tüm odalar bağlı mı?
    - Koridorun en/boy oranı uygun mu?
    """
    connectivity = check_connectivity(rooms)
    connected_count = sum(1 for v in connectivity.values() if v)
    total = len(connectivity)

    if total == 0:
        return 1.0

    connectivity_score = connected_count / total

    # Koridor odalarının en/boy oranı
    corridor_rooms = [r for r in rooms if r.room_type in (RoomType.KORIDOR_DAIRE, RoomType.KORIDOR_BINA)]
    ratio_score = 1.0
    for cr in corridor_rooms:
        aspect = cr.rect.max_dim / cr.rect.min_dim if cr.rect.min_dim > 0 else 999
        if aspect > 6:
            ratio_score *= 0.7  # Çok uzun ve dar koridor
        elif aspect > 4:
            ratio_score *= 0.9

    return connectivity_score * 0.8 + ratio_score * 0.2
