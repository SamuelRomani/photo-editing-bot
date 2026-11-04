"""Leitura e gravação de imagens."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageOps

EXTENSOES = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}


def carregar(caminho: str | Path) -> Image.Image:
    """Abre a imagem, corrige a rotação pelo EXIF e converte para RGB."""
    img = Image.open(caminho)
    img = ImageOps.exif_transpose(img)
    return img.convert("RGB")


def salvar(img: Image.Image, caminho: str | Path, qualidade: int = 95) -> Path:
    """Salva em JPEG de alta qualidade (o Instagram recomprime de qualquer forma)."""
    caminho = Path(caminho).with_suffix(".jpg")
    caminho.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(caminho, "JPEG", quality=qualidade, subsampling=0, optimize=True)
    return caminho


def listar_imagens(pasta: str | Path) -> list[Path]:
    """Lista as imagens suportadas de uma pasta, em ordem alfabética."""
    return sorted(p for p in Path(pasta).iterdir() if p.suffix.lower() in EXTENSOES)
