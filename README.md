# photo-editing-bot

Edição automática de fotos para posts no Instagram, com visual editorial esportivo
(preto e branco dramático, tons frios dessaturados, fundo desfocado). Usa só ferramentas
gratuitas: Pillow/OpenCV para a edição clássica e modelos open source para a parte de IA.

## Roteiro

- [x] **1. Base:** estrutura do projeto, leitura/gravação de fotos, recorte nos formatos do Instagram e linha de comando
- [x] **2. Presets:** brilho, contraste, balanço de branco, "P&B dramático", "Frio dessaturado", vinheta, granulação e cópia de estilo a partir de uma foto de referência
- [x] **3. IA gratuita:** recorte do atleta com rembg para desfocar/escurecer só o fundo; aumento de resolução com redes do OpenCV (FSRCNN, ESPCN, EDSR)
- [x] **4. Interface:** app Gradio com antes/depois, edição em lote e download

## Instalação

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
```

## Uso

Há dois jeitos: a interface web (mais fácil, veja abaixo) e a linha de comando.

### Linha de comando

Coloque as fotos em `entrada/` e rode:

```bash
photobot                    # preset natural, feed (1080x1350), salva em saida/
photobot -f stories         # 1080x1920
photobot minhas_fotos/ prontas/ -f quadrado

photobot -p pb_dramatico                     # P&B de alto contraste
photobot -p nenhum -r referencias/foto.jpg   # copia cor e tom de uma foto de referência
photobot -p frio_dessaturado -r referencias/foto.jpg --forca-referencia 0.5
```

A ordem do processamento é: recorte no formato, cópia de estilo (se houver `-r`) e preset.

Presets:

| Preset             | Visual                                                                 |
|--------------------|------------------------------------------------------------------------|
| `natural`          | Correção limpa: balanço de branco, níveis, contraste e nitidez (padrão) |
| `pb_dramatico`     | Preto e branco com pretos profundos, textura forte, vinheta e granulação |
| `frio_dessaturado` | Cores apagadas, sombras azul-petróleo, contraste cinematográfico        |
| `nenhum`           | Só recorta                                                             |

Os ajustes individuais (brilho, contraste, saturação, balanço de branco, temperatura,
níveis, nitidez, claridade, curva S, vinheta, granulação) ficam em
`src/photobot/ajustes.py` e podem ser combinados para criar novos presets em
`src/photobot/presets.py`.

Formatos disponíveis:

| Formato    | Tamanho     | Uso                         |
|------------|-------------|-----------------------------|
| `feed`     | 1080x1350   | Retrato 4:5, padrão do feed |
| `quadrado` | 1080x1080   | 1:1                         |
| `paisagem` | 1080x566    | 1.91:1                      |
| `stories`  | 1080x1920   | Stories e Reels             |

## Interface web

```bash
pip install -r requirements-app.txt
photobot-app
```

Abra http://127.0.0.1:7860 no navegador. Na aba **Uma foto** você envia a foto,
escolhe estilo, formato, fundo e ajustes finos, compara antes/depois arrastando o
divisor e baixa o JPG. Na aba **Várias fotos** edita um lote inteiro com as mesmas
configurações e baixa tudo num `.zip`. As opções de fundo e super-resolução precisam
das dependências de IA abaixo.

## IA (opcional, gratuita e local)

Instale as dependências extras (o `opencv-contrib` substitui o OpenCV comum):

```bash
pip uninstall -y opencv-python-headless opencv-python
pip install -r requirements-ia.txt
```

```bash
photobot --desfocar-fundo 0.6                          # fundo desfocado, atleta nítido
photobot -p pb_dramatico --desfocar-fundo 0.6 --escurecer-fundo 0.4
photobot --super-resolucao fsrcnn                      # amplia fotos menores que 1080 px
photobot --super-resolucao edsr                        # melhor qualidade, bem mais lento
```

- **Fundo:** o rembg (modelo U²-Net treinado em pessoas) recorta o atleta; o fundo é
  desfocado sem "vazar" a pessoa, então não aparece halo no contorno.
- **Super-resolução:** só é aplicada quando a foto é menor que o formato escolhido.
  `fsrcnn` e `espcn` são rápidos; `edsr` é o de melhor qualidade.

Na primeira vez os modelos são baixados (cerca de 180 MB do rembg em `~/.u2net` ou
`~/.rembg`, e de 40 KB a 40 MB de super-resolução em `~/.cache/photobot`). Depois
tudo roda offline.

## Pastas

- `entrada/`: fotos originais
- `saida/`: fotos editadas
- `referencias/`: fotos de exemplo do estilo desejado (usadas na cópia de estilo)

O conteúdo dessas pastas não vai para o Git, para não publicar fotos de terceiros.

## Testes

```bash
pip install -r requirements-dev.txt
pytest
```
