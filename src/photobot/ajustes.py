"""Ajustes clássicos de imagem (Pillow + NumPy + OpenCV).

Todas as funções recebem e devolvem `PIL.Image` em RGB. Internamente o trabalho é
feito em float32 no intervalo [0, 1] para não perder qualidade entre etapas.
"""

from __future__ import annotations

import cv2
import numpy as np
from PIL import Image

# Pesos de luminância (Rec. 709)
_LUMA = np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)


def para_array(img: Image.Image) -> np.ndarray:
    return np.asarray(img.convert("RGB"), dtype=np.float32) / 255.0


def para_imagem(arr: np.ndarray) -> Image.Image:
    return Image.fromarray((np.clip(arr, 0, 1) * 255 + 0.5).astype(np.uint8), "RGB")


def luminancia(arr: np.ndarray) -> np.ndarray:
    return arr @ _LUMA


# --- Ajustes básicos -------------------------------------------------------

def brilho(img: Image.Image, valor: float) -> Image.Image:
    """Soma `valor` (-1 a 1) à exposição. 0 não muda nada."""
    return para_imagem(para_array(img) + valor)


def contraste(img: Image.Image, fator: float) -> Image.Image:
    """Escala a distância de cada pixel até o cinza médio. 1 não muda nada."""
    arr = para_array(img)
    media = luminancia(arr).mean()
    return para_imagem((arr - media) * fator + media)


def saturacao(img: Image.Image, fator: float) -> Image.Image:
    """0 = preto e branco, 1 = original, >1 = mais saturado."""
    arr = para_array(img)
    cinza = luminancia(arr)[..., None]
    return para_imagem(cinza + (arr - cinza) * fator)


def balanco_branco(img: Image.Image, forca: float = 1.0) -> Image.Image:
    """Balanço de branco automático (gray world robusto).

    Usa só os tons médios (ignora sombras e altas luzes estouradas) para estimar a
    dominante de cor e a neutraliza. `forca` 0..1 controla quanto corrigir.
    """
    arr = para_array(img)
    lum = luminancia(arr)
    mascara = (lum > 0.15) & (lum < 0.9)
    amostra = arr[mascara] if mascara.sum() > 100 else arr.reshape(-1, 3)
    medias = amostra.mean(axis=0)
    ganhos = medias.mean() / np.maximum(medias, 1e-4)
    ganhos = 1 + (ganhos - 1) * forca
    return para_imagem(arr * ganhos)


def temperatura(img: Image.Image, valor: float) -> Image.Image:
    """Esquenta (valor > 0) ou esfria (valor < 0). Faixa útil: -0.3 a 0.3."""
    arr = para_array(img)
    ganhos = np.array([1 + valor, 1.0, 1 - valor], dtype=np.float32)
    return para_imagem(arr * ganhos)


def auto_niveis(img: Image.Image, corte_baixo: float = 0.5, corte_alto: float = 99.5) -> Image.Image:
    """Estica o histograma para usar toda a faixa de preto a branco, sem mudar cores."""
    arr = para_array(img)
    lum = luminancia(arr)
    baixo, alto = np.percentile(lum, [corte_baixo, corte_alto])
    if alto - baixo < 1e-3:
        return img.copy()
    return para_imagem((arr - baixo) / (alto - baixo))


def nitidez(img: Image.Image, quantidade: float = 0.6, raio: float = 1.2) -> Image.Image:
    """Máscara de nitidez (unsharp mask)."""
    arr = para_array(img)
    borrado = cv2.GaussianBlur(arr, (0, 0), raio)
    return para_imagem(arr + (arr - borrado) * quantidade)


def claridade(img: Image.Image, forca: float = 0.5) -> Image.Image:
    """Contraste local (CLAHE na luminância): realça textura do quimono, músculos, rosto."""
    arr = para_array(img)
    lab = cv2.cvtColor(arr, cv2.COLOR_RGB2LAB)
    l8 = np.clip(lab[..., 0] * 2.55, 0, 255).astype(np.uint8)
    clahe = cv2.createCLAHE(clipLimit=2.0 + 2.0 * forca, tileGridSize=(8, 8))
    l_novo = clahe.apply(l8).astype(np.float32) / 2.55
    lab[..., 0] = lab[..., 0] * (1 - forca) + l_novo * forca
    return para_imagem(cv2.cvtColor(lab, cv2.COLOR_LAB2RGB))


# --- Efeitos de estilo -----------------------------------------------------

def curva_s(img: Image.Image, forca: float = 0.5, pretos: float = 0.0) -> Image.Image:
    """Curva em S no contraste (sombras mais escuras, luzes mais claras).

    `pretos` (0..0.2) esmaga as sombras mais profundas para preto puro.
    """
    arr = para_array(img)
    if pretos > 0:
        arr = (arr - pretos) / (1 - pretos)
    arr = np.clip(arr, 0, 1)
    s = arr * arr * (3 - 2 * arr)  # smoothstep
    return para_imagem(arr + (s - arr) * forca * 2)


def preto_e_branco(img: Image.Image, mistura: tuple[float, float, float] = (0.35, 0.5, 0.15)) -> Image.Image:
    """Converte para P&B com mistura de canais (mais vermelho clareia a pele)."""
    arr = para_array(img)
    pesos = np.array(mistura, dtype=np.float32)
    cinza = arr @ (pesos / pesos.sum())
    return para_imagem(np.repeat(cinza[..., None], 3, axis=2))


def tonalizar(
    img: Image.Image,
    sombras: tuple[float, float, float] = (0.0, 0.03, 0.05),
    luzes: tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> Image.Image:
    """Split toning: soma uma cor às sombras e outra às luzes."""
    arr = para_array(img)
    lum = luminancia(arr)[..., None]
    arr = arr + (1 - lum) * np.array(sombras, np.float32) + lum * np.array(luzes, np.float32)
    return para_imagem(arr)


def vinheta(img: Image.Image, forca: float = 0.4, suavidade: float = 0.6) -> Image.Image:
    """Escurece as bordas para levar o olhar ao atleta."""
    arr = para_array(img)
    h, w = arr.shape[:2]
    y, x = np.ogrid[-1:1:complex(0, h), -1:1:complex(0, w)]
    dist = np.sqrt(x * x + y * y) / np.sqrt(2)
    inicio = 1 - suavidade
    mascara = np.clip((dist - inicio * 0.7) / (1 - inicio * 0.7), 0, 1) ** 2
    return para_imagem(arr * (1 - forca * mascara)[..., None])


def granulacao(img: Image.Image, forca: float = 0.04, semente: int | None = 0) -> Image.Image:
    """Granulação de filme, mais visível nos tons médios."""
    arr = para_array(img)
    rng = np.random.default_rng(semente)
    ruido = rng.normal(0, 1, arr.shape[:2]).astype(np.float32)
    ruido = cv2.GaussianBlur(ruido, (0, 0), 0.6)
    lum = luminancia(arr)
    peso = 4 * lum * (1 - lum)  # 0 nos extremos, 1 no meio
    return para_imagem(arr + (ruido * forca * peso)[..., None])
