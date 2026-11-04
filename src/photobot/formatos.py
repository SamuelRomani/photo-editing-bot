"""Formatos do Instagram e recorte/redimensionamento."""

from __future__ import annotations

from PIL import Image, ImageOps

# nome: (largura, altura)
FORMATOS: dict[str, tuple[int, int]] = {
    "feed": (1080, 1350),       # retrato 4:5, o que mais ocupa a tela no feed
    "quadrado": (1080, 1080),   # 1:1
    "paisagem": (1080, 566),    # 1.91:1
    "stories": (1080, 1920),    # 9:16, stories e reels
}


def ajustar_formato(
    img: Image.Image,
    formato: str = "feed",
    centro: tuple[float, float] = (0.5, 0.5),
) -> Image.Image:
    """Recorta para a proporção do formato e redimensiona para o tamanho exato.

    `centro` é o ponto de foco relativo (x, y) entre 0 e 1 usado no recorte.
    """
    if formato not in FORMATOS:
        raise ValueError(f"Formato desconhecido: {formato!r}. Use um de {list(FORMATOS)}")
    tamanho = FORMATOS[formato]
    return ImageOps.fit(img, tamanho, method=Image.Resampling.LANCZOS, centering=centro)
