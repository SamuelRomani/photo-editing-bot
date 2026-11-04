"""Linha de comando: processa uma pasta de fotos."""

from __future__ import annotations

import argparse
from pathlib import Path

from .formatos import FORMATOS, ajustar_formato
from .io import carregar, listar_imagens, salvar


def processar_pasta(entrada: Path, saida: Path, formato: str) -> list[Path]:
    gerados = []
    for caminho in listar_imagens(entrada):
        img = carregar(caminho)
        img = ajustar_formato(img, formato)
        gerados.append(salvar(img, saida / f"{caminho.stem}_{formato}"))
    return gerados


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="photobot", description=__doc__)
    parser.add_argument("entrada", type=Path, nargs="?", default=Path("entrada"), help="pasta com as fotos originais")
    parser.add_argument("saida", type=Path, nargs="?", default=Path("saida"), help="pasta onde salvar as fotos editadas")
    parser.add_argument("-f", "--formato", choices=list(FORMATOS), default="feed")
    args = parser.parse_args(argv)

    gerados = processar_pasta(args.entrada, args.saida, args.formato)
    for g in gerados:
        print(f"✔ {g}")
    print(f"{len(gerados)} foto(s) processada(s).")


if __name__ == "__main__":
    main()
