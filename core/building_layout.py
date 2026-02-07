"""
Bina katı düzeni: Çekirdek + bina koridoru + daire bölgeleri.

Yerleşim stratejisi (çift yüklü koridor):
  - Çekirdek (merdiven şaftı + asansör kuyusu) bir uçta, TAM KAT YÜKSEKLİĞİ
  - Bina koridoru çekirdekten sağa uzanır
  - Daireler koridorun iki yanında sıralanır

  +-----+----+---------+---------+---------+
  |     |    | Daire 1 | Daire 2 | Daire 3 |  <- üst sıra
  | MER | AS +---------+---------+---------+
  | Dİ  | AN |     BİNA KORİDORU           |
  | VEN | SÖR+---------+---------+---------+
  |     |    | Daire 4 | Daire 5 | Daire 6 |  <- alt sıra
  +-----+----+---------+---------+---------+

  Merdiven ve asansör tüm kat yüksekliğini kaplar (şaft/kuyu).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .models import Rect, RoomType, PlacedRoom, FloorPlan, BuildingInput
from .building_codes import BuildingCodes


@dataclass
class BuildingZones:
    """Bina düzeni sonucu."""
    building_rect: Rect
    stairs_rect: Rect
    elevator_rect: Rect | None
    elevator_rect_2: Rect | None       # Çift asansör (Madde 34/4)
    corridor_rect: Rect
    apartment_zones: list[Rect]        # Her dairenin sınır dikdörtgeni
    apartment_corridor_sides: list[str]  # Her daire koridorun hangi tarafında
    warnings: list[str]                # PAİY uyarıları


def compute_building_layout(
    building: BuildingInput,
    codes: BuildingCodes,
) -> BuildingZones:
    """
    Bina katı düzenini hesapla.
    Dış duvar kalınlığı dahil - kullanıcının girdiği boyutlar dış ölçüdür.
    Merdiven ve asansör şaftı/kuyusu binanın tam iç yüksekliğini kaplar.
    PAİY uyumluluk kontrolü yapar ve uyarıları döndürür.
    """
    ow = codes.outer_wall
    W = building.width
    H = building.height
    warnings: list[str] = []

    building_rect = Rect(x=0, y=0, w=W, h=H)

    # İç alan (dış duvarlar çıkarılmış)
    inner_x = ow
    inner_y = ow
    inner_w = W - 2 * ow
    inner_h = H - 2 * ow

    # ── PAİY uyumluluk kontrolleri ────────────────────────────────────

    n_floors = building.num_floors
    total_apartments = building.apartments_per_floor * n_floors

    # Madde 34(1): Asansör zorunluluğu
    if n_floors >= codes.elevator_min_floors_required and not building.has_elevator:
        warnings.append(
            f"⚠️ PAİY Md.34(1): {n_floors} katlı binada asansör zorunludur!"
        )
    elif n_floors >= codes.elevator_min_floors_space and not building.has_elevator:
        warnings.append(
            f"ℹ️ PAİY Md.34(1): {n_floors} katlı binada asansör yeri ayrılmalıdır."
        )

    # Madde 34(4): Çift asansör zorunluluğu
    needs_dual = (
        n_floors >= codes.dual_elevator_floors
        or total_apartments >= codes.dual_elevator_apartments
    )
    if needs_dual:
        warnings.append(
            f"⚠️ PAİY Md.34(4): {n_floors} kat / {total_apartments} daire → "
            f"min 2 asansör zorunlu (10 kat veya 20+ daire)."
        )

    # Madde 34(4): Yangın asansörü
    if n_floors >= codes.fire_elevator_floors:
        warnings.append(
            f"ℹ️ PAİY Md.34(4): {n_floors} katlı binada 1 asansör "
            f"yangına dayanıklı/güç kaynaklı olmalıdır."
        )

    # Madde 34(5): Sedye asansörü
    if n_floors >= codes.raw.get("elevator_shaft", {}).get("stretcher_min_floors", 10):
        warnings.append(
            f"ℹ️ PAİY Md.34(5): {n_floors} katlı binada sedye asansörü "
            f"(min 1.20×2.10m, 2.52m²) zorunludur."
        )

    # ── Çekirdek: Merdiven şaftı + Asansör kuyusu(ları) ──────────────

    stairs_w = codes.stairs_width
    elev_w = codes.elevator_width

    # Merdiven şaftı: sol tarafta, TAM İÇ YÜKSEKLİK
    stairs_rect = Rect(
        x=inner_x,
        y=inner_y,
        w=stairs_w,
        h=inner_h,
    )

    # Asansör kuyusu(ları)
    elevator_rect = None
    elevator_rect_2 = None
    core_total_w = stairs_w

    if building.has_elevator:
        elevator_rect = Rect(
            x=inner_x + stairs_w,
            y=inner_y,
            w=elev_w,
            h=inner_h,
        )
        core_total_w = stairs_w + elev_w

        # Çift asansör: ikinci kuyuyu birincinin yanına koy
        if needs_dual:
            elevator_rect_2 = Rect(
                x=inner_x + stairs_w + elev_w,
                y=inner_y,
                w=elev_w,
                h=inner_h,
            )
            core_total_w = stairs_w + 2 * elev_w

    # ── Bina koridoru ─────────────────────────────────────────────────
    corridor_min_w = codes.building_corridor_width

    corridor_rect = Rect(
        x=inner_x + core_total_w,
        y=inner_y + (inner_h - corridor_min_w) / 2,
        w=inner_w - core_total_w,
        h=corridor_min_w,
    )

    # ── Daire bölgeleri ───────────────────────────────────────────────
    n_apts = building.apartments_per_floor

    n_upper = math.ceil(n_apts / 2)
    n_lower = n_apts - n_upper

    upper_y = corridor_rect.y2
    upper_h = inner_y + inner_h - upper_y

    lower_y = inner_y
    lower_h = corridor_rect.y - inner_y

    available_w = corridor_rect.w
    apt_zones: list[Rect] = []
    apt_sides: list[str] = []

    if n_upper > 0:
        apt_w = available_w / n_upper
        for i in range(n_upper):
            apt_zones.append(Rect(
                x=corridor_rect.x + i * apt_w,
                y=upper_y,
                w=apt_w,
                h=upper_h,
            ))
            apt_sides.append("north")

    if n_lower > 0:
        apt_w = available_w / n_lower
        for i in range(n_lower):
            apt_zones.append(Rect(
                x=corridor_rect.x + i * apt_w,
                y=lower_y,
                w=apt_w,
                h=lower_h,
            ))
            apt_sides.append("south")

    return BuildingZones(
        building_rect=building_rect,
        stairs_rect=stairs_rect,
        elevator_rect=elevator_rect,
        elevator_rect_2=elevator_rect_2,
        corridor_rect=corridor_rect,
        apartment_zones=apt_zones,
        apartment_corridor_sides=apt_sides,
        warnings=warnings,
    )
