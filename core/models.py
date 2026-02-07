"""
Veri modelleri - Kat Planı Üretici v2
Çok daireli bina desteği, duvar kalınlığı, mobilya.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field
import math


# ── Yön (Pusula) ─────────────────────────────────────────────────────────────

class CompassDirection(str, Enum):
    NORTH = "north"
    SOUTH = "south"
    EAST = "east"
    WEST = "west"


# ── Oda Tipleri ───────────────────────────────────────────────────────────────

class RoomType(str, Enum):
    SALON = "salon"
    YATAK_ODASI = "yatak_odasi"
    ODA = "oda"
    MUTFAK = "mutfak"
    BANYO = "banyo"
    TUVALET = "tuvalet"
    ANTRE = "antre"
    KORIDOR_DAIRE = "koridor_daire"     # Daire iç koridoru
    KORIDOR_BINA = "koridor_bina"       # Bina ortak koridoru
    MERDIVEN = "merdiven"
    ASANSOR = "asansor"


ROOM_DISPLAY_NAMES = {
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


# ── Kullanıcı Girdisi ────────────────────────────────────────────────────────

class BuildingInput(BaseModel):
    """Kullanıcının girdiği bina bilgileri."""
    long_side: float = Field(..., gt=0, description="Uzun kenar (metre)")
    short_side: float = Field(..., gt=0, description="Kısa kenar (metre)")
    north_facing: CompassDirection = Field(default=CompassDirection.NORTH)
    num_floors: int = Field(default=1, ge=1)
    has_elevator: bool = Field(default=True)
    apartments_per_floor: int = Field(default=2, ge=1, le=10)

    @property
    def width(self) -> float:
        return self.long_side

    @property
    def height(self) -> float:
        return self.short_side


class RoomCountInput(BaseModel):
    """Her DAİRE için oda sayıları."""
    salon: int = Field(default=1, ge=0)
    yatak_odasi: int = Field(default=2, ge=0)
    oda: int = Field(default=0, ge=0)
    mutfak: int = Field(default=1, ge=0)
    banyo: int = Field(default=1, ge=0)
    tuvalet: int = Field(default=1, ge=0)

    def to_room_list(self) -> list[RoomType]:
        """Oda sayılarını düz listeye çevir."""
        rooms: list[RoomType] = []
        for _ in range(self.salon):
            rooms.append(RoomType.SALON)
        for _ in range(self.yatak_odasi):
            rooms.append(RoomType.YATAK_ODASI)
        for _ in range(self.oda):
            rooms.append(RoomType.ODA)
        for _ in range(self.mutfak):
            rooms.append(RoomType.MUTFAK)
        for _ in range(self.banyo):
            rooms.append(RoomType.BANYO)
        for _ in range(self.tuvalet):
            rooms.append(RoomType.TUVALET)
        return rooms


class UserInput(BaseModel):
    building: BuildingInput
    rooms: RoomCountInput


# ── Geometri ──────────────────────────────────────────────────────────────────

class Rect(BaseModel):
    """Dikdörtgen: sol-alt köşe (x, y) + genişlik + yükseklik."""
    x: float
    y: float
    w: float
    h: float

    @property
    def area(self) -> float:
        return self.w * self.h

    @property
    def cx(self) -> float:
        return self.x + self.w / 2

    @property
    def cy(self) -> float:
        return self.y + self.h / 2

    @property
    def min_dim(self) -> float:
        return min(self.w, self.h)

    @property
    def x2(self) -> float:
        return self.x + self.w

    @property
    def y2(self) -> float:
        return self.y + self.h

    def overlaps(self, other: "Rect") -> bool:
        if self.x >= other.x2 or other.x >= self.x2:
            return False
        if self.y >= other.y2 or other.y >= self.y2:
            return False
        return True

    def touches_edge(self, container: "Rect", tol: float = 0.02) -> dict[str, bool]:
        return {
            "south": abs(self.y - container.y) < tol,
            "north": abs(self.y2 - container.y2) < tol,
            "west": abs(self.x - container.x) < tol,
            "east": abs(self.x2 - container.x2) < tol,
        }

    def shared_edge_length(self, other: "Rect", tol: float = 0.02) -> float:
        # Yatay kenar teması
        if abs(self.x2 - other.x) < tol or abs(other.x2 - self.x) < tol:
            ys = max(self.y, other.y)
            ye = min(self.y2, other.y2)
            return max(0, ye - ys)
        # Dikey kenar teması
        if abs(self.y2 - other.y) < tol or abs(other.y2 - self.y) < tol:
            xs = max(self.x, other.x)
            xe = min(self.x2, other.x2)
            return max(0, xe - xs)
        return 0.0


class Point(BaseModel):
    x: float
    y: float


# ── Kapı/Pencere/Duvar ───────────────────────────────────────────────────────

class DoorPlacement(BaseModel):
    wall_side: str          # "north"/"south"/"east"/"west"
    position: float         # duvar boyunca konum
    width: float = 0.90
    swing_inside: bool = True   # Kapı odanın içine mi açılıyor
    connects_to: Optional[str] = None


class WindowPlacement(BaseModel):
    wall_side: str
    position: float
    width: float = 1.20
    height: float = 1.20


class WallSegment(BaseModel):
    start: Point
    end: Point
    thickness: float
    is_exterior: bool = False


# ── Yerleştirilmiş Oda ───────────────────────────────────────────────────────

class PlacedRoom(BaseModel):
    room_type: RoomType
    room_id: str
    rect: Rect
    doors: list[DoorPlacement] = Field(default_factory=list)
    windows: list[WindowPlacement] = Field(default_factory=list)
    apartment_id: int = 0      # Hangi daire (-1 = ortak alan)
    net_area: Optional[float] = None  # Duvar düşüldükten sonra net alan

    @property
    def area(self) -> float:
        return self.net_area if self.net_area is not None else self.rect.area

    @property
    def label(self) -> str:
        name = ROOM_DISPLAY_NAMES.get(self.room_type, self.room_type.value)
        return f"{name}\n{self.area:.1f} m²"


# ── Kat Planı ─────────────────────────────────────────────────────────────────

class FloorPlan(BaseModel):
    plan_id: str = "plan"
    floor: int = 0
    fitness_score: float = 0.0
    building_rect: Rect
    rooms: list[PlacedRoom] = Field(default_factory=list)
    walls: list[WallSegment] = Field(default_factory=list)
    apartments_per_floor: int = 1

    @property
    def total_room_area(self) -> float:
        return sum(r.area for r in self.rooms)
