"""
Adım 3: Slicing Tree (İkili Uzay Bölümleme) motoru.

Bir dikdörtgeni oda sayısı kadar alt-dikdörtgene böler.
Her bölme: yatay veya dikey kesim + kesim oranı.

Genom temsili:
  - cut_orientations: [0 veya 1] * (n_rooms - 1)  → 0=dikey, 1=yatay
  - cut_ratios: [0.2 .. 0.8] * (n_rooms - 1)      → kesim pozisyonu oranı
  - room_assignment: permütasyon [0..n_rooms-1]     → yaprak-oda eşlemesi
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Optional

from .models import Rect


@dataclass
class SlicingNode:
    """İkili bölme ağacı düğümü."""
    rect: Optional[Rect] = None         # Hesaplanmış dikdörtgen
    orientation: int = 0                 # 0=dikey (V), 1=yatay (H)
    ratio: float = 0.5                   # Kesim oranı (0-1)
    left: Optional["SlicingNode"] = None
    right: Optional["SlicingNode"] = None
    leaf_index: Optional[int] = None     # Yapraksa, yaprak sıra numarası

    @property
    def is_leaf(self) -> bool:
        return self.left is None and self.right is None


def build_tree(n_leaves: int, orientations: list[int], ratios: list[float]) -> SlicingNode:
    """
    n_leaves yapraklı dengeli bir slicing tree oluştur.
    orientations ve ratios listeleri uzunluğu = n_leaves - 1.
    
    Recursive olarak:
    - 1 yaprak -> yaprak düğüm (parametre gerekmez)
    - n yaprak -> 1 kesim parametresi + sol(n//2) + sağ(n - n//2)
    - Toplam parametre: n - 1 (her iç düğüm için 1)
    """
    if n_leaves <= 0:
        raise ValueError("En az 1 yaprak gerekli")

    if n_leaves == 1:
        return SlicingNode(leaf_index=0)

    # Parametre yetersizse varsayılan kullan
    if not orientations or not ratios:
        orientations = [0] * (n_leaves - 1)
        ratios = [0.5] * (n_leaves - 1)

    # Dengeli bölme: sol tarafa yarısı, sağ tarafa kalanı
    left_count = n_leaves // 2
    right_count = n_leaves - left_count

    # Bu düğümün kesimi (ilk parametre)
    node = SlicingNode(
        orientation=orientations[0],
        ratio=ratios[0],
    )

    # Kalan parametreleri sol ve sağ alt ağaçlara dağıt
    # Sol alt ağaç: (left_count - 1) parametre gerekiyor
    # Sağ alt ağaç: (right_count - 1) parametre gerekiyor
    left_n_params = max(0, left_count - 1)
    right_n_params = max(0, right_count - 1)

    left_orientations = orientations[1:1 + left_n_params]
    left_ratios = ratios[1:1 + left_n_params]

    right_orientations = orientations[1 + left_n_params:1 + left_n_params + right_n_params]
    right_ratios = ratios[1 + left_n_params:1 + left_n_params + right_n_params]

    node.left = build_tree(left_count, left_orientations, left_ratios)
    node.right = build_tree(right_count, right_orientations, right_ratios)

    return node


def compute_rects(node: SlicingNode, container: Rect) -> None:
    """Ağaçtaki her düğümün dikdörtgenini hesapla (yerinde günceller)."""
    node.rect = container

    if node.is_leaf:
        return

    if node.orientation == 0:
        # Dikey kesim: sol ve sağ
        split_x = container.x + container.w * node.ratio
        left_rect = Rect(x=container.x, y=container.y, w=split_x - container.x, h=container.h)
        right_rect = Rect(x=split_x, y=container.y, w=container.x + container.w - split_x, h=container.h)
    else:
        # Yatay kesim: alt ve üst
        split_y = container.y + container.h * node.ratio
        left_rect = Rect(x=container.x, y=container.y, w=container.w, h=split_y - container.y)
        right_rect = Rect(x=container.x, y=split_y, w=container.w, h=container.y + container.h - split_y)

    if node.left:
        compute_rects(node.left, left_rect)
    if node.right:
        compute_rects(node.right, right_rect)


def get_leaves(node: SlicingNode) -> list[SlicingNode]:
    """Tüm yaprak düğümlerini döndür (sol-sağ sırasıyla)."""
    if node.is_leaf:
        return [node]
    result = []
    if node.left:
        result.extend(get_leaves(node.left))
    if node.right:
        result.extend(get_leaves(node.right))
    return result


def assign_leaf_indices(node: SlicingNode, counter: list[int] | None = None) -> None:
    """Yapraklara sıralı index ata."""
    if counter is None:
        counter = [0]
    if node.is_leaf:
        node.leaf_index = counter[0]
        counter[0] += 1
        return
    if node.left:
        assign_leaf_indices(node.left, counter)
    if node.right:
        assign_leaf_indices(node.right, counter)


# ── Genom İşlemleri ──────────────────────────────────────────────────────────

@dataclass
class SlicingGenome:
    """GA için slicing tree genomu."""
    n_rooms: int
    orientations: list[int]    # 0 veya 1, uzunluk = n_rooms - 1
    ratios: list[float]        # 0.2-0.8, uzunluk = n_rooms - 1
    room_order: list[int]      # permütasyon [0..n_rooms-1]

    def to_rects(self, container: Rect) -> list[Rect]:
        """Genomu dikdörtgen listesine çevir. room_order[i] = i. yapraktaki oda indeksi."""
        if self.n_rooms == 0:
            return []
        if self.n_rooms == 1:
            return [container]

        tree = build_tree(self.n_rooms, self.orientations, self.ratios)
        assign_leaf_indices(tree)
        compute_rects(tree, container)

        leaves = get_leaves(tree)
        # room_order'a göre sırala: room_order[i] indeksli oda, i. yaprakta
        rects = [Rect(x=0, y=0, w=0, h=0)] * self.n_rooms
        for leaf_idx, leaf in enumerate(leaves):
            if leaf_idx < len(self.room_order) and leaf.rect:
                room_idx = self.room_order[leaf_idx]
                rects[room_idx] = leaf.rect

        return rects


def random_genome(n_rooms: int) -> SlicingGenome:
    """Rastgele bir genom üret."""
    n_cuts = max(0, n_rooms - 1)
    return SlicingGenome(
        n_rooms=n_rooms,
        orientations=[random.randint(0, 1) for _ in range(n_cuts)],
        ratios=[random.uniform(0.25, 0.75) for _ in range(n_cuts)],
        room_order=random.sample(range(n_rooms), n_rooms),
    )


def mutate_genome(genome: SlicingGenome, mutation_rate: float = 0.2) -> SlicingGenome:
    """Genomda küçük değişiklikler yap."""
    n_cuts = max(0, genome.n_rooms - 1)

    new_orientations = list(genome.orientations)
    new_ratios = list(genome.ratios)
    new_order = list(genome.room_order)

    for i in range(n_cuts):
        if random.random() < mutation_rate:
            new_orientations[i] = 1 - new_orientations[i]  # flip
        if random.random() < mutation_rate:
            new_ratios[i] = max(0.2, min(0.8, new_ratios[i] + random.gauss(0, 0.1)))

    # Oda sırası mutasyonu: iki odayı yer değiştir
    if random.random() < mutation_rate and len(new_order) >= 2:
        i, j = random.sample(range(len(new_order)), 2)
        new_order[i], new_order[j] = new_order[j], new_order[i]

    return SlicingGenome(
        n_rooms=genome.n_rooms,
        orientations=new_orientations,
        ratios=new_ratios,
        room_order=new_order,
    )


def crossover_genomes(a: SlicingGenome, b: SlicingGenome) -> SlicingGenome:
    """İki genomu çaprazla."""
    n_cuts = max(0, a.n_rooms - 1)

    # Tek nokta çaprazlama (orientations + ratios)
    if n_cuts > 0:
        cx = random.randint(0, n_cuts - 1)
        new_o = a.orientations[:cx] + b.orientations[cx:]
        new_r = a.ratios[:cx] + b.ratios[cx:]
    else:
        new_o = []
        new_r = []

    # Order çaprazlama: Order Crossover (OX)
    new_order = _order_crossover(a.room_order, b.room_order)

    return SlicingGenome(
        n_rooms=a.n_rooms,
        orientations=new_o,
        ratios=new_r,
        room_order=new_order,
    )


def _order_crossover(parent_a: list[int], parent_b: list[int]) -> list[int]:
    """Order Crossover (OX1) for permutations."""
    n = len(parent_a)
    if n <= 2:
        return list(parent_a)

    start = random.randint(0, n - 2)
    end = random.randint(start + 1, n - 1)

    child = [-1] * n
    # A'dan bir dilimi kopyala
    child[start:end + 1] = parent_a[start:end + 1]

    # B'den kalanları sırayla doldur
    b_remaining = [x for x in parent_b if x not in child]
    fill_idx = 0
    for i in range(n):
        if child[i] == -1:
            child[i] = b_remaining[fill_idx]
            fill_idx += 1

    return child
