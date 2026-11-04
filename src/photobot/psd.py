"""Gravação de PSD em camadas, sem dependências além de NumPy e Pillow.

O PSD abre no PhotoCraft, no Photoshop, no GIMP, no Krita e no Photopea, então dá
para refinar à mão o que o bot fez: comparar com a original, ajustar a máscara do
atleta, mudar a opacidade da edição etc.

Implementa só o necessário do formato (especificação pública da Adobe): RGB 8 bits,
camadas de pixels com ou sem transparência, dados sem compressão.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image


@dataclass
class Camada:
    nome: str
    imagem: Image.Image
    mascara: np.ndarray | None = None  # float 0..1 (vira a transparência da camada)
    visivel: bool = True
    opacidade: float = 1.0


def _canais(camada: Camada, tamanho: tuple[int, int]) -> list[tuple[int, bytes]]:
    img = camada.imagem.convert("RGB")
    if img.size != tamanho:
        raise ValueError(f"A camada {camada.nome!r} tem {img.size}, o documento tem {tamanho}")
    rgb = np.asarray(img, dtype=np.uint8)
    canais = [(i, rgb[..., i].tobytes()) for i in range(3)]
    if camada.mascara is not None:
        m = np.asarray(camada.mascara, dtype=np.float32)
        if m.shape != rgb.shape[:2]:
            raise ValueError(f"A máscara da camada {camada.nome!r} não tem o tamanho da imagem")
        alfa = np.clip(np.round(m * 255), 0, 255).astype(np.uint8)
        canais.insert(0, (-1, alfa.tobytes()))
    return canais


def _nome_pascal(nome: str) -> bytes:
    """Nome em Pascal string (MacRoman), com o tamanho total múltiplo de 4."""
    b = nome.encode("mac_roman", errors="replace")[:255]
    dado = bytes([len(b)]) + b
    return dado + b"\0" * (-len(dado) % 4)


def _nome_unicode(nome: str) -> bytes:
    """Bloco 'luni': o nome em UTF-16, para acentos aparecerem certos."""
    txt = nome.encode("utf-16-be")
    dado = struct.pack(">I", len(txt) // 2) + txt
    dado += b"\0" * (-len(dado) % 4)
    return b"8BIMluni" + struct.pack(">I", len(dado)) + dado


def salvar_psd(camadas: list[Camada], caminho: str | Path, composta: Image.Image | None = None) -> Path:
    """Salva as camadas (a primeira fica embaixo) num PSD.

    `composta` é a imagem achatada que aparece em visualizadores sem suporte a
    camadas; por padrão é a camada visível mais de cima.
    """
    if not camadas:
        raise ValueError("Informe pelo menos uma camada")
    caminho = Path(caminho).with_suffix(".psd")
    caminho.parent.mkdir(parents=True, exist_ok=True)
    largura, altura = camadas[0].imagem.size
    if composta is None:
        composta = next((c.imagem for c in reversed(camadas) if c.visivel), camadas[-1].imagem)

    registros, dados = b"", b""
    for camada in camadas:
        canais = _canais(camada, (largura, altura))
        reg = struct.pack(">4iH", 0, 0, altura, largura, len(canais))
        for id_canal, px in canais:
            reg += struct.pack(">hI", id_canal, len(px) + 2)
            dados += struct.pack(">H", 0) + px  # 0 = sem compressão
        flags = 0 if camada.visivel else 0b10
        opacidade = int(round(np.clip(camada.opacidade, 0, 1) * 255))
        reg += b"8BIMnorm" + struct.pack(">BBBB", opacidade, 0, flags, 0)
        extra = struct.pack(">II", 0, 0) + _nome_pascal(camada.nome) + _nome_unicode(camada.nome)
        reg += struct.pack(">I", len(extra)) + extra
        registros += reg

    info = struct.pack(">h", len(camadas)) + registros + dados
    info += b"\0" * (len(info) % 2)
    secao_camadas = struct.pack(">I", len(info)) + info + struct.pack(">I", 0)

    rgb = np.asarray(composta.convert("RGB"), dtype=np.uint8)
    if rgb.shape[:2] != (altura, largura):
        raise ValueError("A imagem composta não tem o tamanho do documento")

    with open(caminho, "wb") as f:
        f.write(b"8BPS" + struct.pack(">H6xHIIHH", 1, 3, altura, largura, 8, 3))
        f.write(struct.pack(">I", 0))  # dados de modo de cor
        f.write(struct.pack(">I", 0))  # recursos de imagem
        f.write(struct.pack(">I", len(secao_camadas)) + secao_camadas)
        f.write(struct.pack(">H", 0) + np.ascontiguousarray(rgb.transpose(2, 0, 1)).tobytes())
    return caminho
