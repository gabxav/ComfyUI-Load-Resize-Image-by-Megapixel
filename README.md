# Load & Resize Image by Megapixel

Node do ComfyUI que carrega uma imagem (com seletor, upload e preview, igual ao **Load Image** nativo) e já
redimensiona para um alvo em megapixels, com largura e altura divisíveis por N.

Exemplo: `1.0 MP` divisível por `32` → uma foto 1920×1080 vira 1344×736; uma 960×1280 vira 864×1152.

## Nodes

- **Load & Resize Image by Megapixel** (`image`): Load Image + resize.
- **Resize Image by Megapixel** (`image/transform`): mesmo resize para um `IMAGE` vindo de outro node
  (aceita `MASK` opcional).

## Widgets

| Widget | Efeito |
|---|---|
| `image` | Imagem da pasta `input` (upload e preview como no Load Image) |
| `resize` | Desligado: devolve a imagem no tamanho original |
| `megapixels` | Alvo em MP (padrão `1.0` = 1.000.000 pixels) |
| `divisible_by` | 8, 16, 32, 64, 112 ou 128 (padrão `32`) |
| `upscale_method` | lanczos, bicubic, bilinear, area, nearest-exact |
| `rounding` | `nearest` fica o mais perto do alvo; `floor` nunca passa dele; `ceil` nunca fica abaixo |
| `fit_mode` | `crop` mantém a proporção cortando do centro os pixels perdidos no arredondamento; `stretch` distorce levemente |
| `only_downscale` | **Só reduzir**: imagens com área menor ou igual ao MP selecionado passam intactas; imagens maiores são reduzidas sem ultrapassar o limite. Desligado por padrão (**Permitir ampliar**) |

## Só reduzir

Ative `resize` e `only_downscale` para usar `megapixels` como um teto. O controle existe nos dois nodes.

Com `1.0 MP` e `divisible_by=32`:

- 640×640 continua 640×640, sem reamostragem.
- 1000×1000 continua 1000×1000, mesmo sem ser múltiplo de 32.
- 2048×2048 vira 992×992 (984.064 pixels).

Nesse modo, imagens acima do teto usam sempre arredondamento `floor`, independentemente do widget `rounding`,
para respeitar o limite. `divisible_by`, o método de interpolação e `fit_mode` só são aplicados quando há redução.
Máscaras reais acompanham o resize; imagens preservadas mantêm também a máscara original.
Se o limite e o múltiplo escolhido não permitirem a redução, o node apresenta um erro pedindo mais MP ou um múltiplo menor.
`resize` desligado sempre devolve o original, independentemente de `only_downscale`.

Workflows antigos continuam com o comportamento anterior: o novo controle é opcional e assume `false` quando ausente.
Os controles existentes conservam sua ordem. O arquivo enviado por upload não é alterado; o resize ocorre ao executar o workflow.

## Saídas

`IMAGE`, `width`, `height`, `MASK` (alpha da imagem, redimensionado junto).

## Instalação

```sh
cd ComfyUI/custom_nodes
git clone https://github.com/gabxav/ComfyUI-Load-Resize-Image-by-Megapixel.git
```

Reinicie o ComfyUI. Sem dependências além das do próprio ComfyUI.

## Testes

No ambiente Python do ComfyUI, execute:

```sh
PYTHONPATH=/caminho/ComfyUI python tests/test_resize.py
```

Os testes usam os nodes e o resize reais do ComfyUI em CPU, sem carregar modelos.
