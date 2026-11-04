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
    desfoque_fundo: float = 0.0,
    escurecer_fundo: float = 0.0,
    super_resolucao: str | None = None,
) -> Image.Image:
    """Pipeline completo.

    1. Aumenta a resolução, se pedido e se a foto for pequena (IA)
    2. Recorta no formato do Instagram
    3. Copia o estilo da referência (opcional)
    4. Desfoca/escurece o fundo (IA, opcional)
    5. Aplica o preset (vinheta e granulação ficam por último, como num filme)
    """
    if super_resolucao:
        from .ia import garantir_resolucao

        img = garantir_resolucao(img, FORMATOS[formato][0], super_resolucao)
    img = ajustar_formato(img, formato)
    if referencia is not None:
        img = transferir_estilo(img, referencia, forca_referencia)
    if desfoque_fundo > 0 or escurecer_fundo > 0:
        from .ia import desfocar_fundo

        img = desfocar_fundo(img, desfoque_fundo, escurecer_fundo)
    return aplicar_preset(img, preset)


def processar_pasta(
    entrada: Path,
    saida: Path,
    formato: str = "feed",
    preset: str = "natural",
    referencia: Path | None = None,
    forca_referencia: float = 1.0,
    **opcoes_ia,
) -> list[Path]:
    ref = carregar(referencia) if referencia else None
    gerados = []
    for caminho in listar_imagens(entrada):
        img = editar(carregar(caminho), formato, preset, ref, forca_referencia, **opcoes_ia)
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
    ia = parser.add_argument_group("IA (requer: pip install -r requirements-ia.txt)")
    ia.add_argument("--desfocar-fundo", type=float, default=0.0, metavar="0-1", help="desfoca o fundo atrás do atleta")
    ia.add_argument("--escurecer-fundo", type=float, default=0.0, metavar="0-1", help="escurece o fundo atrás do atleta")
    ia.add_argument(
        "--super-resolucao", choices=["fsrcnn", "espcn", "edsr"], help="aumenta a resolução de fotos pequenas"
    )
    args = parser.parse_args(argv)

    gerados = processar_pasta(
        args.entrada,
        args.saida,
        args.formato,
        args.preset,
        args.referencia,
        args.forca_referencia,
        desfoque_fundo=args.desfocar_fundo,
        escurecer_fundo=args.escurecer_fundo,
        super_resolucao=args.super_resolucao,
    )
    for g in gerados:
        print(f"✔ {g}")
    print(f"{len(gerados)} foto(s) processada(s).")


if __name__ == "__main__":
    main()
