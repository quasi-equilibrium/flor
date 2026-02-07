"""
Adım 4: Merdiven ve asansör çekirdek elemanlarını yerleştir.
Çekirdek elemanlar sabit pozisyona yerleştirilir, kalan alan slicing tree'ye verilir.
"""

from __future__ import annotations

from .models import Rect, RoomType, PlacedRoom
from .building_codes import BuildingCodes


class CorePlacement:
    """Çekirdek (merdiven + asansör) yerleştirme sonucu."""

    def __init__(
        self,
        stairs_rect: Rect | None,
        elevator_rect: Rect | None,
        remaining_rects: list[Rect],
    ):
        self.stairs_rect = stairs_rect
        self.elevator_rect = elevator_rect
        self.remaining_rects = remaining_rects  # Kalan alanlar (slicing tree için)

    def to_placed_rooms(self) -> list[PlacedRoom]:
        rooms = []
        if self.stairs_rect:
            rooms.append(PlacedRoom(
                room_type=RoomType.MERDIVEN,
                room_id="merdiven_0",
                rect=self.stairs_rect,
            ))
        if self.elevator_rect:
            rooms.append(PlacedRoom(
                room_type=RoomType.ASANSOR,
                room_id="asansor_0",
                rect=self.elevator_rect,
            ))
        return rooms


def place_core(
    inner_rect: Rect,
    codes: BuildingCodes,
    has_elevator: bool = False,
    position: str = "center_left",
) -> CorePlacement:
    """
    Çekirdek elemanları yerleştir ve kalan alanı döndür.
    
    Pozisyon seçenekleri:
      - "center_left": sol ortada (varsayılan)
      - "center_right": sağ ortada
      - "top_center": üst ortada
      - "bottom_center": alt ortada
    
    Merdiven + asansör yan yana yerleştirilir.
    Kalan alan: çekirdeğin solunda ve sağında (veya üstünde/altında) iki bölge.
    Eğer çekirdek yoksa, inner_rect'in tamamı döner.
    """
    stairs_w = codes.stairs_width
    stairs_l = codes.stairs_length

    # Çekirdek toplam boyutu
    core_w = stairs_w
    core_l = stairs_l

    if has_elevator:
        elev_w = codes.elevator_width
        elev_l = codes.elevator_length
        # Asansör merdivenin yanına
        core_w = stairs_w + elev_w + codes.inner_wall
    else:
        elev_w = 0
        elev_l = 0

    # Çekirdek yoksa (nadir ama olabilir)
    need_stairs = True  # Merdiven her zaman var

    if not need_stairs:
        return CorePlacement(None, None, [inner_rect])

    # Pozisyona göre çekirdeği yerleştir
    if position == "center_left":
        core_x = inner_rect.x
        core_y = inner_rect.cy - core_l / 2
    elif position == "center_right":
        core_x = inner_rect.x2 - core_w
        core_y = inner_rect.cy - core_l / 2
    elif position == "top_center":
        core_x = inner_rect.cx - core_w / 2
        core_y = inner_rect.y2 - core_l
    elif position == "bottom_center":
        core_x = inner_rect.cx - core_w / 2
        core_y = inner_rect.y
    else:
        core_x = inner_rect.x
        core_y = inner_rect.cy - core_l / 2

    # Sınır kontrolü
    core_y = max(inner_rect.y, min(core_y, inner_rect.y2 - core_l))
    core_x = max(inner_rect.x, min(core_x, inner_rect.x2 - core_w))

    # Merdiven rect
    stairs_rect = Rect(x=core_x, y=core_y, w=stairs_w, h=stairs_l)

    # Asansör rect (merdivenin sağında)
    elevator_rect = None
    if has_elevator:
        elevator_rect = Rect(
            x=core_x + stairs_w + codes.inner_wall,
            y=core_y,
            w=elev_w,
            h=max(elev_l, stairs_l),
        )

    # Kalan alanları hesapla
    remaining = _compute_remaining_area(inner_rect, core_x, core_y, core_w, core_l)

    return CorePlacement(stairs_rect, elevator_rect, remaining)


def _compute_remaining_area(
    container: Rect,
    core_x: float,
    core_y: float,
    core_w: float,
    core_h: float,
) -> list[Rect]:
    """
    Çekirdeği çıkardıktan sonra kalan alanları L-şeklinde veya
    tek büyük dikdörtgen olarak döndür.
    
    Strateji: Çekirdeğin konumuna göre en büyük dikdörtgeni seç.
    Basit yaklaşım: çekirdeği tam bir şerit olarak kesip, kalan alanı döndür.
    """
    # Çekirdeği dikey şerit olarak kes
    # Sol kalan
    left_w = core_x - container.x
    # Sağ kalan
    right_x = core_x + core_w
    right_w = container.x2 - right_x
    # Üst kalan (çekirdeğin üstü, çekirdek genişliğinde)
    top_y = core_y + core_h
    top_h = container.y2 - top_y
    # Alt kalan (çekirdeğin altı)
    bottom_h = core_y - container.y

    rects = []

    # Ana büyük alan: çekirdeğin sağındaki tüm alan
    if right_w > 1.0:
        rects.append(Rect(x=right_x, y=container.y, w=right_w, h=container.h))

    # Çekirdeğin üstündeki alan (sol şerit üstü)
    if top_h > 1.0 and left_w > 0.5:
        rects.append(Rect(x=container.x, y=top_y, w=core_w + (0 if rects else right_w), h=top_h))

    # Çekirdeğin altındaki alan (sol şerit altı)
    if bottom_h > 1.0 and left_w > 0.5:
        rects.append(Rect(x=container.x, y=container.y, w=core_w + (0 if rects else right_w), h=bottom_h))

    # Eğer hiçbir anlamlı alan yoksa, tüm alanı döndür (çekirdek sığmamış)
    if not rects:
        rects.append(container)

    # En büyük dikdörtgeni ilk sıraya koy (ana oda alanı olarak)
    rects.sort(key=lambda r: r.area, reverse=True)

    return rects


# Çekirdek pozisyon seçenekleri (GA için)
CORE_POSITIONS = ["center_left", "center_right", "top_center", "bottom_center"]
