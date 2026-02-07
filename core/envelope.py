"""
Adım 2: Bina zarfı işlemleri.
Dikdörtgen bina sınırı oluşturma, net alan hesaplama, yön bilgisi.
"""

from __future__ import annotations

from .models import BuildingInput, CompassDirection, Rect
from .building_codes import BuildingCodes


def create_building_rect(building: BuildingInput) -> Rect:
    """Bina dış sınırı dikdörtgeni oluştur. Orijin (0,0) sol-alt köşe."""
    return Rect(x=0, y=0, w=building.width, h=building.height)


def create_inner_rect(building_rect: Rect, codes: BuildingCodes) -> Rect:
    """Dış duvar kalınlığını çıkararak iç (net) alanı hesapla."""
    t = codes.outer_wall
    return Rect(
        x=building_rect.x + t,
        y=building_rect.y + t,
        w=building_rect.w - 2 * t,
        h=building_rect.h - 2 * t,
    )


def get_compass_edges(building_rect: Rect, north_facing: CompassDirection) -> dict[str, str]:
    """
    Dikdörtgenin kenarlarını pusula yönlerine eşle.
    
    building_rect kenarları: "top", "bottom", "left", "right"
    Dönüş: {"north": "top", "south": "bottom", "east": "right", "west": "left"}
    (north_facing=NORTH varsayılan durumda)
    """
    # "top" kenarı north_facing yönüne bakıyor
    # Saat yönünde: top -> right -> bottom -> left
    edges = ["top", "right", "bottom", "left"]
    compass = ["north", "east", "south", "west"]

    # north_facing'e göre top kenarını eşle
    offset_map = {
        CompassDirection.NORTH: 0,  # top = north
        CompassDirection.EAST: 1,   # top = east  (bina 90° sola döndürülmüş)
        CompassDirection.SOUTH: 2,  # top = south (bina 180° döndürülmüş)
        CompassDirection.WEST: 3,   # top = west  (bina 90° sağa döndürülmüş)
    }
    offset = offset_map[north_facing]

    result = {}
    for i, direction in enumerate(compass):
        edge_idx = (i + offset) % 4
        result[direction] = edges[edge_idx]

    return result


def edge_to_wall_side(edge: str) -> str:
    """Kenar adını rect wall_side'a çevir."""
    mapping = {"top": "north", "bottom": "south", "left": "west", "right": "east"}
    return mapping.get(edge, edge)


def get_exterior_walls(room_rect: Rect, building_rect: Rect, tolerance: float = 0.01) -> list[str]:
    """Odanın hangi dış duvarlara değdiğini döndür."""
    touches = room_rect.touches_edge(building_rect, tolerance)
    return [side for side, val in touches.items() if val]
