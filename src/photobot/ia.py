"""Recursos de IA gratuitos e locais (sem API paga).

- Recorte do atleta com rembg (modelo U²-Net para pessoas) para desfocar e escurecer
  só o fundo, imitando o efeito de lente clara das fotos de referência.
- Aumento de resolução com as redes de super-resolução do OpenCV (EDSR, ESPCN, FSRCNN).

Os modelos são baixados automaticamente na primeira vez e ficam em cache. As
dependências são opcionais: `pip install -r requirements-ia.txt`.
"""

from __future__ import annotations

import urllib.request
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from .ajustes import para_array, para_imagem

PASTA_MODELOS = Path.home() / ".cache" / "photobot"

_URL_SR = {
    "edsr": "https://raw.githubusercontent.com/Saafke/EDSR_Tensorflow/master/models/EDSR_x{escala}.pb",
    "espcn": "https://raw.githubusercontent.com/fannymonori/TF-ESPCN/master/export/ESPCN_x{escala}.pb",
    "fsrcnn": "https://raw.githubusercontent.com/Saafke/FSRCNN_Tensorflow/master/models/FSRCNN_x{escala}.pb",
}
MODELOS_SR = list(_URL_SR)


class DependenciaFaltando(RuntimeError):
    pass


# --- Recorte do atleta / fundo ---------------------------------------------

@lru_cache(maxsize=2)
def _sessao_rembg(modelo: str):
    try:
        from rembg import new_session
    except ImportError as e:
        raise DependenciaFaltando(
            "Para recortar o atleta instale as dependências de IA: pip install -r requirements-ia.txt"
        ) from e
    return new_session(modelo)


def mascara_pessoa(img: Image.Image, modelo: str = "u2net_human_seg") -> np.ndarray:
    """Máscara float [0, 1] com 1 onde está a pessoa."""
    from rembg import remove

    mascara = remove(img, session=_sessao_rembg(modelo), only_mask=True)
    return np.asarray(mascara.convert("L"), dtype=np.float32) / 255.0


def suavizar_mascara(mascara: np.ndarray, raio: float = 3.0) -> np.ndarray:
    """Suaviza a borda da máscara para a transição pessoa/fundo não ficar recortada."""
    if raio <= 0:
        return mascara
    return np.clip(cv2.GaussianBlur(mascara, (0, 0), raio), 0, 1)


def desfocar_fundo(
    img: Image.Image,
    forca: float = 0.5,
    escurecer: float = 0.0,
    mascara: np.ndarray | None = None,
) -> Image.Image:
    """Desfoca (e opcionalmente escurece) tudo que não é a pessoa.

    `forca` 0..1 controla o desfoque (proporcional ao tamanho da foto), `escurecer`
    0..1 quanto o fundo perde de luz. Passe `mascara` para reaproveitar uma já calculada.
    """
    arr = para_array(img)
    if mascara is None:
        mascara = mascara_pessoa(img)
    m = suavizar_mascara(mascara, max(arr.shape[:2]) / 400)[..., None]

    fundo = arr
    if forca > 0:
        # Desfoque "normalizado": a pessoa é tirada antes de borrar, senão ela vaza
        # para o fundo e cria um halo claro em volta do contorno.
        sigma = forca * max(arr.shape[:2]) / 80
        peso = 1 - np.clip(mascara, 0, 1)[..., None]
        soma = cv2.GaussianBlur(arr * peso, (0, 0), sigma)
        norma = cv2.GaussianBlur(peso, (0, 0), sigma)[..., None]
        fundo = np.where(norma > 1e-3, soma / np.maximum(norma, 1e-3), arr)
    fundo = fundo * (1 - escurecer)
    return para_imagem(arr * m + fundo * (1 - m))


# --- Aumento de resolução ---------------------------------------------------

def _baixar_modelo_sr(modelo: str, escala: int) -> Path:
    destino = PASTA_MODELOS / f"{modelo.upper()}_x{escala}.pb"
    if not destino.exists():
        destino.parent.mkdir(parents=True, exist_ok=True)
        url = _URL_SR[modelo].format(escala=escala)
        tmp = destino.with_suffix(".tmp")
        urllib.request.urlretrieve(url, tmp)
        tmp.rename(destino)
    return destino


@lru_cache(maxsize=4)
def _rede_sr(modelo: str, escala: int):
    if not hasattr(cv2, "dnn_superres"):
        raise DependenciaFaltando(
            "Para aumentar a resolução instale o OpenCV contrib: pip install -r requirements-ia.txt"
        )
    rede = cv2.dnn_superres.DnnSuperResImpl_create()
    rede.readModel(str(_baixar_modelo_sr(modelo, escala)))
    rede.setModel(modelo, escala)
    return rede


def aumentar_resolucao(img: Image.Image, escala: int = 2, modelo: str = "fsrcnn") -> Image.Image:
    """Aumenta a resolução com uma rede neural.

    `modelo`: "fsrcnn" (rápido), "espcn" (rápido) ou "edsr" (melhor qualidade, bem
    mais lento). `escala`: 2, 3 ou 4.
    """
    if modelo not in _URL_SR:
        raise ValueError(f"Modelo desconhecido: {modelo!r}. Use um de {MODELOS_SR}")
    if escala not in (2, 3, 4):
        raise ValueError("A escala deve ser 2, 3 ou 4")
    bgr = cv2.cvtColor(np.asarray(img.convert("RGB")), cv2.COLOR_RGB2BGR)
    saida = _rede_sr(modelo, escala).upsample(bgr)
    return Image.fromarray(cv2.cvtColor(saida, cv2.COLOR_BGR2RGB))


def garantir_resolucao(img: Image.Image, largura_minima: int = 1080, modelo: str = "fsrcnn") -> Image.Image:
    """Aumenta a resolução só se a foto for menor que o necessário para o Instagram."""
    falta = largura_minima / min(img.size)
    if falta <= 1:
        return img
    escala = 2 if falta <= 2 else 3 if falta <= 3 else 4
    return aumentar_resolucao(img, escala, modelo)
