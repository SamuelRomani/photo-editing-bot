"""Linha de comando: processa uma pasta de fotos."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image

from .estilo import transferir_estilo
from .formatos import FORMATOS, ajustar_formato
from .io import carregar, listar_imagens, salvar
from .presets import PRESETS, aplicar_preset


def editar(
    img: Image.Image,
    formato: str = "feed",
    preset: str = "natural",
    referencia: Image.Image | None = None,
    forca_referencia: float = 1.0,
) -> Image.Image:
    """Pipeline completo: recorta no formato, copia o estilo (opcional) e aplica o preset.

    O recorte vem primeiro para que a vinheta e o enquadramento fiquem certos na foto
    final e o processamento seja mais rápido.
    """
    img = ajustar_formato(img, formato)
    if referencia is not None:
        img = transferir_estilo(img, referencia, forca_referencia)
    return aplicar_preset(img, preset)


def processar_pasta(
    entrada: Path,
    saida: Path,
    formato: str = "feed",
    preset: str = "natural",
    referencia: Path | None = None,
    forca_referencia: float = 1.0,
) -> list[Path]:
    ref = carregar(referencia) if referencia else None
    gerados = []
    for caminho in listar_imagens(entrada):
        img = editar(carregar(caminho), formato, preset, ref, forca_referencia)
        gerados.append(salvar(img, saida / f"{caminho.stem}_{preset}_{formato}"))
    return gerados


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="photobot", description=__doc__)
    parser.add_argument("entrada", type=Path, nargs="?", default=Path("entrada"), help="pasta com as fotos originais")
    parser.add_argument("saida", type=Path, nargs="?", default=Path("saida"), help="pasta onde salvar as fotos editadas")
    parser.add_argument("-f", "--formato", choices=list(FORMATOS), default="feed")
    parser.add_argument("-p", "--preset", choices=list(PRESETS), default="natural")
    parser.add_argument("-r", "--referencia", type=Path, help="foto cujo estilo de cor/tom será copiado")
    parser.add_argument("--forca-referencia", type=float, default=0.8, help="0 a 1 (padrão 0.8)")
    args = parser.parse_args(argv)

    gerados = processar_pasta(
        args.entrada, args.saida, args.formato, args.preset, args.referencia, args.forca_referencia
    )
    for g in gerados:
        print(f"✔ {g}")
    print(f"{len(gerados)} foto(s) processada(s).")


if __name__ == "__main__":
    main()
