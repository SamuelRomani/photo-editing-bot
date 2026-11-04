"""Cópia de estilo: transfere cores e tons de uma foto de referência."""

from __future__ import annotations

import cv2
import numpy as np
from PIL import Image

from .ajustes import para_array, para_imagem


def transferir_estilo(img: Image.Image, referencia: Image.Image, forca: float = 1.0) -> Image.Image:
    """Transferência de cor de Reinhard no espaço LAB.

    Ajusta média e desvio de luminosidade e cor da foto para ficarem iguais aos da
    referência. Se a referência for P&B, o resultado sai P&B. `forca` 0..1.
    """
    origem = cv2.cvtColor(para_array(img), cv2.COLOR_RGB2LAB)
    ref = cv2.cvtColor(para_array(referencia.resize((512, 512))), cv2.COLOR_RGB2LAB)

    m_o, d_o = origem.reshape(-1, 3).mean(0), origem.reshape(-1, 3).std(0)
    m_r, d_r = ref.reshape(-1, 3).mean(0), ref.reshape(-1, 3).std(0)
    resultado = (origem - m_o) * (d_r / np.maximum(d_o, 1e-4)) + m_r

    resultado = origem + (resultado - origem) * forca
    return para_imagem(cv2.cvtColor(resultado.astype(np.float32), cv2.COLOR_LAB2RGB))
