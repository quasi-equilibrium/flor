"""
Türk Yapı Yönetmeliği kısıtları - PAİY (Planlı Alanlar İmar Yönetmeliği) uyumlu.
Madde referansları: 5, 23, 28, 29, 30, 31, 32, 34, 38, 39.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from .models import RoomType

DEFAULT_CONFIG_PATH = Path(__file__).parent.parent / "config" / "building_codes_tr.json"


class BuildingCodes:
    def __init__(self, config_path: Optional[Path] = None):
        self._path = config_path or DEFAULT_CONFIG_PATH
        self._data: dict = {}
        self.load()

    def load(self) -> None:
        with open(self._path, "r", encoding="utf-8") as f:
            self._data = json.load(f)

    def save(self) -> None:
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)

    @property
    def raw(self) -> dict:
        return self._data

    # ── A) Oda / Piyes Minimumları (Madde 29) ────────────────────────

    def min_area(self, room_type: RoomType) -> float:
        return self._data.get("min_areas", {}).get(room_type.value, 0.0)

    def preferred_area_ratio(self, room_type: RoomType) -> float:
        return self._data.get("preferred_area_ratios", {}).get(room_type.value, 0.10)

    def min_width(self, room_type: RoomType) -> float:
        return self._data.get("min_widths", {}).get(room_type.value, 1.0)

    @property
    def mandatory_rooms(self) -> list[str]:
        """Madde 5(25), 29(1): zorunlu piyes listesi."""
        return self._data.get("mandatory_rooms", {}).get(
            "list", ["salon", "yatak_odasi", "mutfak", "banyo", "tuvalet"]
        )

    # ── B) Dolaşım Alanları (Madde 29, 30) ──────────────────────────

    @property
    def building_corridor_width(self) -> float:
        """Madde 30(1): Bina koridor/giriş holü min genişlik."""
        return self._data.get("building_corridor", {}).get("min_width", 1.50)

    @property
    def apartment_corridor_width(self) -> float:
        """Madde 29(3): Daire içi hol/koridor min genişlik."""
        return self._data.get("apartment_corridor", {}).get("min_width", 1.20)

    @property
    def building_entry_width(self) -> float:
        """Madde 30(1): Bina giriş holü min genişlik."""
        return self._data.get("building_entry", {}).get("min_width", 1.50)

    # ── C) Merdiven (Madde 31, 38) ──────────────────────────────────

    @property
    def stairs_width(self) -> float:
        return self._data.get("stairs", {}).get("width", 3.0)

    @property
    def stairs_length(self) -> float:
        return self._data.get("stairs", {}).get("length", 6.0)

    @property
    def stair_arm_width(self) -> float:
        """Madde 31(1a): Konut ortak merdiven kolu min 1.20m."""
        return self._data.get("stairs", {}).get("arm_width", 1.20)

    @property
    def stair_arm_width_internal(self) -> float:
        """Madde 31(1a): Daire içi merdiven min 1.00m."""
        return self._data.get("stairs", {}).get("arm_width_internal", 1.00)

    @property
    def stair_riser_max(self) -> float:
        """Madde 31(2a): Asansörlü binada max rıht yüksekliği 0.18m."""
        return self._data.get("stairs", {}).get("riser_max_with_elevator", 0.18)

    @property
    def stair_riser_max_no_elevator(self) -> float:
        """Madde 31(2a): Asansörsüz binada max rıht yüksekliği 0.16m."""
        return self._data.get("stairs", {}).get("riser_max_without_elevator", 0.16)

    @property
    def stair_tread_min(self) -> float:
        """Madde 31(2b): Basamak genişliği min 0.27m."""
        return self._data.get("stairs", {}).get("tread_min", 0.27)

    @property
    def stair_landing_min_width(self) -> float:
        """Madde 31(1a): Kat sahanlığı min genişlik (= kol genişliği)."""
        return self._data.get("stairs", {}).get("landing_min_width", 1.20)

    @property
    def handrail_height(self) -> float:
        """Madde 38(1): Korkuluk yüksekliği min 1.10m."""
        return self._data.get("stairs", {}).get("handrail_height", 1.10)

    # ── D) Asansör (Madde 5, 34) ────────────────────────────────────

    @property
    def elevator_width(self) -> float:
        return self._data.get("elevator_shaft", {}).get("width", 2.5)

    @property
    def elevator_length(self) -> float:
        return self._data.get("elevator_shaft", {}).get("length", 2.5)

    @property
    def elevator_min_floors_required(self) -> int:
        """Madde 34(1): 4+ kat: asansör montajı zorunlu."""
        return self._data.get("elevator_shaft", {}).get("min_floors_required", 4)

    @property
    def elevator_min_floors_space(self) -> int:
        """Madde 34(1): 3 kat: asansör yeri ayrılmalı."""
        return self._data.get("elevator_shaft", {}).get("min_floors_space", 3)

    @property
    def dual_elevator_floors(self) -> int:
        """Madde 34(4): 10 kat veya 20+ dairede çift asansör zorunlu."""
        return self._data.get("elevator_shaft", {}).get("dual_elevator_floors", 10)

    @property
    def dual_elevator_apartments(self) -> int:
        """Madde 34(4): 20+ dairede çift asansör zorunlu."""
        return self._data.get("elevator_shaft", {}).get("dual_elevator_apartments", 20)

    @property
    def fire_elevator_floors(self) -> int:
        """Madde 34(4): 10+ katlı binalarda yangın asansörü zorunlu."""
        return self._data.get("elevator_shaft", {}).get("fire_elevator_floors", 10)

    @property
    def elevator_cabin_min_width(self) -> float:
        """Madde 34(2): Tek asansör kabin dar kenarı min 1.20m."""
        return self._data.get("elevator_shaft", {}).get("cabin_min_width", 1.20)

    @property
    def elevator_cabin_min_area(self) -> float:
        """Madde 34(2): Tek asansör kabin alanı min 1.80m²."""
        return self._data.get("elevator_shaft", {}).get("cabin_min_area", 1.80)

    @property
    def elevator_door_min_width(self) -> float:
        """Madde 34(2): Asansör kapı net geçiş min 0.90m."""
        return self._data.get("elevator_shaft", {}).get("door_min_width", 0.90)

    # ── E) Kapı ve Pencere (Madde 39) ───────────────────────────────

    def door_width(self, room_type: RoomType) -> float:
        doors = self._data.get("doors", {})
        key = room_type.value
        if key in doors and isinstance(doors[key], dict):
            return doors[key].get("width", 0.90)
        return doors.get("standard", {}).get("width", 0.90)

    @property
    def building_entry_door_width(self) -> float:
        """Madde 39(1b): Bina giriş kapısı min 1.50m."""
        return self._data.get("doors", {}).get("bina_giris", {}).get("width", 1.50)

    @property
    def apartment_entry_door_width(self) -> float:
        """Madde 39(1c): Daire giriş kapısı min 1.00m."""
        return self._data.get("doors", {}).get("giris", {}).get("width", 1.00)

    # ── F) Duvar ve Kat Yükseklikleri (Madde 28) ────────────────────

    @property
    def outer_wall(self) -> float:
        return self._data.get("walls", {}).get("outer_thickness", 0.25)

    @property
    def inner_wall(self) -> float:
        return self._data.get("walls", {}).get("inner_thickness", 0.15)

    @property
    def carrier_wall(self) -> float:
        return self._data.get("walls", {}).get("carrier_thickness", 0.20)

    @property
    def floor_height(self) -> float:
        return self._data.get("floor_height", 2.80)

    @property
    def floor_height_max(self) -> float:
        """Madde 28(1c): Konut brüt kat yüksekliği max 3.60m."""
        return self._data.get("floor_height_max", 3.60)

    @property
    def min_ceiling_height(self) -> float:
        """Madde 28(4): İskân edilen kat iç yüksekliği min 2.60m."""
        return self._data.get("min_ceiling_height", 2.60)

    @property
    def wet_area_ceiling_height(self) -> float:
        """Madde 28(5): Islak hacim/koridor tavan yüksekliği min 2.20m."""
        return self._data.get("wet_area_ceiling_height", 2.20)

    # ── G) Parsel ve Yerleşim (Madde 23, 32) ────────────────────────

    @property
    def setback_front(self) -> float:
        """Madde 23(1a): Ön bahçe min 5.00m."""
        return self._data.get("setbacks", {}).get("front_min", 5.00)

    @property
    def setback_side(self) -> float:
        """Madde 23(1b): Yan bahçe min 3.00m (4 kata kadar)."""
        return self._data.get("setbacks", {}).get("side_min", 3.00)

    @property
    def setback_rear(self) -> float:
        """Madde 23(1c): Arka bahçe min 3.00m (4 kata kadar)."""
        return self._data.get("setbacks", {}).get("rear_min", 3.00)

    @property
    def setback_floor_increment(self) -> float:
        """Madde 23(1ç): 4 katın üzerinde her kat için +0.50m."""
        return self._data.get("setbacks", {}).get("floor_increment", 0.50)

    @property
    def setback_floor_increment_base(self) -> int:
        """4 kata kadar sabit, sonra artış başlar."""
        return self._data.get("setbacks", {}).get("floor_increment_base", 4)

    def setback_for_floors(self, n_floors: int, side: str = "side") -> float:
        """Verilen kat sayısı için bahçe mesafesini hesapla."""
        base = self.setback_front if side == "front" else (
            self.setback_side if side == "side" else self.setback_rear
        )
        extra_floors = max(0, n_floors - self.setback_floor_increment_base)
        return base + extra_floors * self.setback_floor_increment

    def lightwell_min(self, n_floors: int) -> tuple[float, float]:
        """Madde 32: Kat sayısına göre ışıklık min kenar ve alan."""
        lw = self._data.get("lightwell", {})
        if n_floors <= lw.get("small_max_floors", 6):
            return lw.get("small_min_edge", 1.50), lw.get("small_min_area", 4.50)
        return lw.get("large_min_edge", 2.00), lw.get("large_min_area", 9.00)

    @property
    def air_shaft_size(self) -> tuple[float, float]:
        """Madde 32(3): Hava bacası min 0.60×0.60m."""
        lw = self._data.get("lightwell", {})
        return lw.get("air_shaft_width", 0.60), lw.get("air_shaft_length", 0.60)

    # ── H) Islak Hacim / Yangın ─────────────────────────────────────

    @property
    def wet_area_types(self) -> list[str]:
        return self._data.get("wet_area_types", ["mutfak", "banyo", "tuvalet"])

    def is_wet_area(self, room_type: RoomType) -> bool:
        return room_type.value in self.wet_area_types

    def needs_exterior_wall(self, room_type: RoomType) -> bool:
        return room_type in (
            RoomType.SALON, RoomType.YATAK_ODASI, RoomType.ODA, RoomType.MUTFAK,
        )

    def needs_window(self, room_type: RoomType) -> bool:
        return room_type in (
            RoomType.SALON, RoomType.YATAK_ODASI, RoomType.ODA, RoomType.MUTFAK,
        )

    @property
    def requires_separate_stairs_mixed_use(self) -> bool:
        """Madde 31(5): Karma kullanımda ayrı merdiven evi zorunlu."""
        return self._data.get("fire_safety", {}).get("separate_stairs_mixed_use", True)

    # ── Diğer ────────────────────────────────────────────────────────

    @property
    def adjacency_rules(self) -> dict[str, str]:
        return self._data.get("adjacency_rules", {})
