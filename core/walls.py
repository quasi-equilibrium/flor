"""
Adım 8: Duvar kalınlığı, kapı ve pencere yerleşimi.
Oda sınırları belirlenmiş plan üzerinde:
- Duvarları çiz
- Kapıları yerleştir
- Pencereleri yerleştir
"""

from __future__ import annotations

from .models import (
    Rect, RoomType, PlacedRoom, FloorPlan,
    WallSegment, DoorPlacement, WindowPlacement, Point,
)
from .building_codes import BuildingCodes
from .envelope import get_exterior_walls
from .corridor import find_neighbors


def add_walls_and_openings(plan: FloorPlan, codes: BuildingCodes) -> FloorPlan:
    """
    Plana duvar, kapı ve pencere ekle.
    Yerinde günceller ve geri döndürür.
    """
    building_rect = plan.building_rect

    # 1. Duvarları oluştur
    plan.walls = _generate_walls(plan.rooms, building_rect, codes)

    # 2. Komşuluk grafiği
    neighbors = find_neighbors(plan.rooms)

    # Oda lookup
    room_map = {r.room_id: r for r in plan.rooms}

    # 3. Kapıları yerleştir
    for room in plan.rooms:
        if room.room_type in (RoomType.MERDIVEN, RoomType.ASANSOR):
            continue

        room.doors = _place_doors(room, neighbors, room_map, codes)

    # 4. Pencereleri yerleştir
    for room in plan.rooms:
        room.windows = _place_windows(room, building_rect, codes)

    return plan


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

    # Alt duvar (güney)
    walls.append(WallSegment(start=Point(x=bx, y=by), end=Point(x=bx2, y=by), thickness=ow, is_exterior=True))
    # Üst duvar (kuzey)
    walls.append(WallSegment(start=Point(x=bx, y=by2), end=Point(x=bx2, y=by2), thickness=ow, is_exterior=True))
    # Sol duvar (batı)
    walls.append(WallSegment(start=Point(x=bx, y=by), end=Point(x=bx, y=by2), thickness=ow, is_exterior=True))
    # Sağ duvar (doğu)
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

            shared = ra.rect.shared_edge_length(rb.rect)
            if shared < 0.1:
                continue

            processed.add(key)

            # Paylaşılan kenarı bul
            wall = _find_shared_wall(ra.rect, rb.rect, iw)
            if wall:
                walls.append(wall)

    return walls


def _find_shared_wall(a: Rect, b: Rect, thickness: float) -> WallSegment | None:
    """İki dikdörtgen arasındaki paylaşılan duvarı bul."""
    tol = 0.05

    # Sağ-Sol temas (a'nın sağı b'nin solu)
    if abs(a.x2 - b.x) < tol:
        ys = max(a.y, b.y)
        ye = min(a.y2, b.y2)
        if ye > ys:
            return WallSegment(
                start=Point(x=a.x2, y=ys),
                end=Point(x=a.x2, y=ye),
                thickness=thickness,
            )

    # Sol-Sağ temas
    if abs(b.x2 - a.x) < tol:
        ys = max(a.y, b.y)
        ye = min(a.y2, b.y2)
        if ye > ys:
            return WallSegment(
                start=Point(x=a.x, y=ys),
                end=Point(x=a.x, y=ye),
                thickness=thickness,
            )

    # Üst-Alt temas (a'nın üstü b'nin altı)
    if abs(a.y2 - b.y) < tol:
        xs = max(a.x, b.x)
        xe = min(a.x2, b.x2)
        if xe > xs:
            return WallSegment(
                start=Point(x=xs, y=a.y2),
                end=Point(x=xe, y=a.y2),
                thickness=thickness,
            )

    # Alt-Üst temas
    if abs(b.y2 - a.y) < tol:
        xs = max(a.x, b.x)
        xe = min(a.x2, b.x2)
        if xe > xs:
            return WallSegment(
                start=Point(x=xs, y=a.y),
                end=Point(x=xe, y=a.y),
                thickness=thickness,
            )

    return None


def _place_doors(
    room: PlacedRoom,
    neighbors: dict[str, list[str]],
    room_map: dict[str, PlacedRoom],
    codes: BuildingCodes,
) -> list[DoorPlacement]:
    """Odaya kapı yerleştir. En az 1 kapı, koridora veya komşuya açılır."""
    doors: list[DoorPlacement] = []
    door_width = codes.door_width(room.room_type)
    room_neighbors = neighbors.get(room.room_id, [])

    if not room_neighbors:
        return doors

    # Öncelik: koridora açılsın, yoksa en büyük komşuya
    best_neighbor = None
    best_shared = 0.0

    for nid in room_neighbors:
        neighbor = room_map.get(nid)
        if not neighbor:
            continue

        shared = room.rect.shared_edge_length(neighbor.rect)

        # Koridor tercih edilir
        is_corridor = neighbor.room_type == RoomType.KORIDOR
        priority = shared + (10.0 if is_corridor else 0.0)

        if priority > best_shared:
            best_shared = priority
            best_neighbor = neighbor

    if best_neighbor:
        door = _create_door_on_shared_wall(room, best_neighbor, door_width)
        if door:
            door.connects_to = best_neighbor.room_id
            doors.append(door)

    return doors


def _create_door_on_shared_wall(
    room: PlacedRoom,
    neighbor: PlacedRoom,
    door_width: float,
) -> DoorPlacement | None:
    """Paylaşılan duvarda kapı oluştur."""
    tol = 0.05
    a = room.rect
    b = neighbor.rect
    margin = 0.30  # Köşeden min mesafe

    # Sağ kenar
    if abs(a.x2 - b.x) < tol or abs(b.x2 - a.x) < tol:
        ys = max(a.y, b.y) + margin
        ye = min(a.y2, b.y2) - margin
        if ye - ys >= door_width:
            pos = (ys + ye) / 2
            side = "east" if abs(a.x2 - b.x) < tol else "west"
            return DoorPlacement(wall_side=side, position=pos, width=door_width)

    # Üst/Alt kenar
    if abs(a.y2 - b.y) < tol or abs(b.y2 - a.y) < tol:
        xs = max(a.x, b.x) + margin
        xe = min(a.x2, b.x2) - margin
        if xe - xs >= door_width:
            pos = (xs + xe) / 2
            side = "north" if abs(a.y2 - b.y) < tol else "south"
            return DoorPlacement(wall_side=side, position=pos, width=door_width)

    return None


def _place_windows(
    room: PlacedRoom,
    building_rect: Rect,
    codes: BuildingCodes,
) -> list[WindowPlacement]:
    """Dış duvardaki odalara pencere yerleştir."""
    if not codes.needs_window(room.room_type):
        return []

    windows: list[WindowPlacement] = []
    exterior_sides = get_exterior_walls(room.rect, building_rect)

    if not exterior_sides:
        return []

    # İlk dış duvara pencere koy
    side = exterior_sides[0]
    win_height = codes.window_standard_height
    min_win_w = codes.window_min_width

    # Pencere genişliği: oda alanının %10'u / pencere yüksekliği, min 0.6m
    required_area = room.area * codes.window_min_area_ratio
    win_w = max(min_win_w, required_area / win_height)

    # Duvar genişliğine göre sınırla
    if side in ("north", "south"):
        max_w = room.rect.w - 0.6  # Kenarlarda 30cm boşluk
        pos = room.rect.cx
    else:
        max_w = room.rect.h - 0.6
        pos = room.rect.cy

    win_w = min(win_w, max(min_win_w, max_w))

    windows.append(WindowPlacement(
        wall_side=side,
        position=pos,
        width=win_w,
        height=win_height,
    ))

    # Balkon: ek pencere (kapı görevi de görür)
    if len(exterior_sides) > 1 and room.room_type == RoomType.SALON:
        side2 = exterior_sides[1]
        windows.append(WindowPlacement(
            wall_side=side2,
            position=room.rect.cx if side2 in ("north", "south") else room.rect.cy,
            width=min_win_w,
            height=win_height,
        ))

    return windows
