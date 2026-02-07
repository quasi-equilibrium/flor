"""
Adım 5: Fitness (uygunluk) fonksiyonları.
Her plan alternatifinin kalitesini 0-1 arası puanlama.
"""

from __future__ import annotations

from .models import Rect, RoomType, PlacedRoom, FloorPlan
from .building_codes import BuildingCodes


def evaluate_fitness(
    rooms: list[PlacedRoom],
    building_rect: Rect,
    target_areas: list[float],
    codes: BuildingCodes,
) -> float:
    """
    Plan kalitesini 0-1 arası puanla.
    
    Bileşenler:
    1. Alan dağılımı skoru (hedef alanlara yakınlık)
    2. Minimum alan/genişlik uyumu (sert kısıt)
    3. Dış duvar erişimi skoru
    4. Komşuluk skoru
    5. Kompaktlık (toplam alan verimliliği)
    """
    if not rooms:
        return 0.0

    scores = []
    weights = []

    # 1. Alan dağılımı (ağırlık: 0.30)
    area_score = _area_distribution_score(rooms, target_areas)
    scores.append(area_score)
    weights.append(0.30)

    # 2. Minimum kısıt uyumu (ağırlık: 0.25)
    constraint_score = _constraint_score(rooms, codes)
    scores.append(constraint_score)
    weights.append(0.25)

    # 3. Dış duvar erişimi (ağırlık: 0.20)
    exterior_score = _exterior_access_score(rooms, building_rect, codes)
    scores.append(exterior_score)
    weights.append(0.20)

    # 4. Komşuluk (ağırlık: 0.15)
    adj_score = _adjacency_score(rooms, codes)
    scores.append(adj_score)
    weights.append(0.15)

    # 5. Kompaktlık (ağırlık: 0.10)
    compact_score = _compactness_score(rooms, building_rect)
    scores.append(compact_score)
    weights.append(0.10)

    total = sum(s * w for s, w in zip(scores, weights))
    return max(0.0, min(1.0, total))


def _area_distribution_score(rooms: list[PlacedRoom], target_areas: list[float]) -> float:
    """Her odanın alanının hedef alana ne kadar yakın olduğu."""
    if not target_areas or len(rooms) != len(target_areas):
        return 0.5

    total_error = 0.0
    for room, target in zip(rooms, target_areas):
        if target <= 0:
            continue
        error = abs(room.area - target) / target
        total_error += min(error, 1.0)  # max %100 hata

    avg_error = total_error / len(rooms)
    return max(0.0, 1.0 - avg_error)


def _constraint_score(rooms: list[PlacedRoom], codes: BuildingCodes) -> float:
    """Minimum alan ve genişlik kısıtlarına uyum."""
    if not rooms:
        return 0.0

    violations = 0
    total_checks = 0

    for room in rooms:
        rt = room.room_type
        # Koridor ve çekirdek elemanları atla
        if rt in (RoomType.KORIDOR_DAIRE, RoomType.KORIDOR_BINA, RoomType.MERDIVEN, RoomType.ASANSOR):
            continue

        # Minimum alan
        min_a = codes.min_area(rt)
        if min_a > 0:
            total_checks += 1
            if room.area < min_a * 0.9:  # %10 tolerans
                violations += 1

        # Minimum genişlik
        min_w = codes.min_width(rt)
        if min_w > 0:
            total_checks += 1
            if room.rect.min_dim < min_w * 0.9:
                violations += 1

    if total_checks == 0:
        return 1.0
    return max(0.0, 1.0 - (violations / total_checks))


def _exterior_access_score(
    rooms: list[PlacedRoom],
    building_rect: Rect,
    codes: BuildingCodes,
) -> float:
    """Dış duvar gerektiren odaların gerçekten dış duvara erişimi var mı."""
    need_exterior = 0
    has_exterior = 0

    for room in rooms:
        if codes.needs_exterior_wall(room.room_type):
            need_exterior += 1
            touches = room.rect.touches_edge(building_rect, tolerance=0.05)
            if any(touches.values()):
                has_exterior += 1

    if need_exterior == 0:
        return 1.0
    return has_exterior / need_exterior


def _adjacency_score(rooms: list[PlacedRoom], codes: BuildingCodes) -> float:
    """Komşuluk kurallarına uyum skoru."""
    rules = codes.adjacency_rules
    if not rules:
        return 1.0

    satisfied = 0
    total = 0

    # Oda tipine göre hızlı lookup
    rooms_by_type: dict[str, list[PlacedRoom]] = {}
    for r in rooms:
        rt = r.room_type.value
        if rt not in rooms_by_type:
            rooms_by_type[rt] = []
        rooms_by_type[rt].append(r)

    for rule_key, relation in rules.items():
        parts = rule_key.split("_")
        if len(parts) < 2:
            continue

        # "mutfak_salon" -> mutfak ve salon bitişik olmalı
        if relation == "adjacent":
            type_a = parts[0]
            type_b = parts[1]
            if type_a in rooms_by_type and type_b in rooms_by_type:
                total += 1
                for ra in rooms_by_type[type_a]:
                    for rb in rooms_by_type[type_b]:
                        if ra.rect.shared_edge_length(rb.rect) > 0.5:
                            satisfied += 1
                            break
                    else:
                        continue
                    break

        elif relation == "near":
            type_a = parts[0]
            type_b = parts[1]
            if type_a in rooms_by_type and type_b in rooms_by_type:
                total += 1
                for ra in rooms_by_type[type_a]:
                    for rb in rooms_by_type[type_b]:
                        # "Yakın" = merkezler arası mesafe < 8m
                        dist = ((ra.rect.cx - rb.rect.cx) ** 2 + (ra.rect.cy - rb.rect.cy) ** 2) ** 0.5
                        if dist < 8.0:
                            satisfied += 1
                            break
                    else:
                        continue
                    break

    if total == 0:
        return 1.0
    return satisfied / total


def _compactness_score(rooms: list[PlacedRoom], building_rect: Rect) -> float:
    """Alan kullanım verimliliği."""
    total_room_area = sum(r.area for r in rooms)
    if building_rect.area <= 0:
        return 0.0
    efficiency = total_room_area / building_rect.area
    # %60-90 arası iyi
    if efficiency > 0.90:
        return 1.0
    elif efficiency > 0.60:
        return (efficiency - 0.60) / 0.30
    else:
        return efficiency / 0.60 * 0.5
