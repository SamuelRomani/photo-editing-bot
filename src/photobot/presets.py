"""Presets prontos, inspirados nas fotos de referência (editorial esportivo escuro)."""

from __future__ import annotations

from typing import Callable

from PIL import Image

from . import ajustes as a


def natural(img: Image.Image) -> Image.Image:
    """Correção limpa: balanço de branco, níveis, um pouco de contraste e nitidez."""
    img = a.balanco_branco(img)
    img = a.auto_niveis(img)
    img = a.curva_s(img, 0.2)
    img = a.claridade(img, 0.25)
    return a.nitidez(img, 0.4)


def pb_dramatico(img: Image.Image) -> Image.Image:
    """P&B de alto contraste, pretos profundos e textura forte."""
    img = a.balanco_branco(img)
    img = a.preto_e_branco(img)
    img = a.auto_niveis(img, 1, 99.7)
    img = a.claridade(img, 0.6)
    img = a.preto_e_branco(img)  # remove resíduo de cor do arredondamento no LAB
    img = a.curva_s(img, 0.45, pretos=0.06)
    img = a.vinheta(img, 0.45)
    img = a.nitidez(img, 0.5)
    return a.granulacao(img, 0.035)


def frio_dessaturado(img: Image.Image) -> Image.Image:
    """Cores apagadas, sombras azul-petróleo, contraste cinematográfico."""
    img = a.balanco_branco(img)
    img = a.auto_niveis(img)
    img = a.saturacao(img, 0.45)
    img = a.temperatura(img, -0.06)
    img = a.claridade(img, 0.4)
    img = a.curva_s(img, 0.35, pretos=0.04)
    img = a.tonalizar(img, sombras=(-0.02, 0.03, 0.05), luzes=(0.02, 0.01, 0.0))
    img = a.vinheta(img, 0.35)
    img = a.nitidez(img, 0.4)
    return a.granulacao(img, 0.025)


PRESETS: dict[str, Callable[[Image.Image], Image.Image]] = {
    "nenhum": lambda img: img,
    "natural": natural,
    "pb_dramatico": pb_dramatico,
    "frio_dessaturado": frio_dessaturado,
}


def aplicar_preset(img: Image.Image, nome: str) -> Image.Image:
    if nome not in PRESETS:
        raise ValueError(f"Preset desconhecido: {nome!r}. Use um de {list(PRESETS)}")
    return PRESETS[nome](img)
