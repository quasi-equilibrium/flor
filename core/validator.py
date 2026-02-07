"""
Adım 9: Plan doğrulama motoru.
Üretilen planları tüm kısıtlara karşı kontrol eder.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .models import Rect, RoomType, PlacedRoom, FloorPlan
from .building_codes import BuildingCodes
from .corridor import check_connectivity, find_neighbors


@dataclass
class ValidationResult:
    """Doğrulama sonucu."""
    is_valid: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def add_error(self, msg: str) -> None:
        self.errors.append(msg)
        self.is_valid = False

    def add_warning(self, msg: str) -> None:
        self.warnings.append(msg)


def validate_plan(plan: FloorPlan, codes: BuildingCodes) -> ValidationResult:
    """Planı tüm kurallara karşı doğrula."""
    result = ValidationResult()

    _check_overlaps(plan, result)
    _check_bounds(plan, result)
    _check_min_areas(plan, codes, result)
    _check_min_widths(plan, codes, result)
    _check_connectivity(plan, result)
    _check_exterior_access(plan, codes, result)

    return result


def _check_overlaps(plan: FloorPlan, result: ValidationResult) -> None:
    """Oda çakışması kontrolü."""
    rooms = plan.rooms
    for i in range(len(rooms)):
        for j in range(i + 1, len(rooms)):
            ri, rj = rooms[i], rooms[j]
            if ri.rect.overlaps(rj.rect):
                # Komşu kenar teması OK, gerçek çakışma değil
                # Küçük çakışmaları (< 0.01 m²) tolere et
                ix1 = max(ri.rect.x, rj.rect.x)
                iy1 = max(ri.rect.y, rj.rect.y)
                ix2 = min(ri.rect.x2, rj.rect.x2)
                iy2 = min(ri.rect.y2, rj.rect.y2)
                overlap_area = max(0, ix2 - ix1) * max(0, iy2 - iy1)
                if overlap_area > 0.05:
                    result.add_error(
                        f"Çakışma: {ri.room_id} ve {rj.room_id} "
                        f"({overlap_area:.2f} m² çakışma)"
                    )


def _check_bounds(plan: FloorPlan, result: ValidationResult) -> None:
    """Tüm odalar bina sınırı içinde mi?"""
    br = plan.building_rect
    for room in plan.rooms:
        r = room.rect
        if r.x < br.x - 0.01 or r.y < br.y - 0.01:
            result.add_error(f"{room.room_id} bina sınırı dışında (sol/alt)")
        if r.x2 > br.x2 + 0.01 or r.y2 > br.y2 + 0.01:
            result.add_error(f"{room.room_id} bina sınırı dışında (sağ/üst)")


def _check_min_areas(plan: FloorPlan, codes: BuildingCodes, result: ValidationResult) -> None:
    """Minimum alan kontrolü."""
    for room in plan.rooms:
        if room.room_type in (RoomType.KORIDOR_DAIRE, RoomType.KORIDOR_BINA, RoomType.MERDIVEN, RoomType.ASANSOR):
            continue
        min_a = codes.min_area(room.room_type)
        if min_a > 0 and room.area < min_a * 0.85:  # %15 tolerans
            result.add_warning(
                f"{room.room_id}: alan {room.area:.1f} m² < min {min_a:.1f} m²"
            )


def _check_min_widths(plan: FloorPlan, codes: BuildingCodes, result: ValidationResult) -> None:
    """Minimum genişlik kontrolü."""
    for room in plan.rooms:
        if room.room_type in (RoomType.KORIDOR_DAIRE, RoomType.KORIDOR_BINA, RoomType.MERDIVEN, RoomType.ASANSOR):
            continue
        min_w = codes.min_width(room.room_type)
        if min_w > 0 and room.rect.min_dim < min_w * 0.85:
            result.add_warning(
                f"{room.room_id}: min genişlik {room.rect.min_dim:.2f}m < {min_w:.2f}m"
            )


def _check_connectivity(plan: FloorPlan, result: ValidationResult) -> None:
    """Her oda en az bir komşuya bağlı mı?"""
    connectivity = check_connectivity(plan.rooms)
    for room_id, connected in connectivity.items():
        if not connected:
            result.add_warning(f"{room_id}: hiçbir odaya bağlantısı yok")


def _check_exterior_access(
    plan: FloorPlan, codes: BuildingCodes, result: ValidationResult
) -> None:
    """Dış duvar gerektiren odalar gerçekten dış duvarda mı?"""
    for room in plan.rooms:
        if codes.needs_exterior_wall(room.room_type):
            touches = room.rect.touches_edge(plan.building_rect, tolerance=0.05)
            if not any(touches.values()):
                result.add_warning(
                    f"{room.room_id} ({room.room_type.value}): dış duvara erişimi yok"
                )
