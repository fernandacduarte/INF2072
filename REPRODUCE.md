# Reproduzindo o resultado (IQL, fantasmas cooperativos)

Guia passo a passo para reproduzir nosso resultado: **IQL com 3 fantasmas
cooperativos que aprendem a encurralar o Pac-Man** (~70% de captura em 1M
frames), no maze `pinklike3` com a política de reward `capture_v0_closing`.

O modelo treinado (o melhor checkpoint) **já vem versionado no repositório**,
então dá para ver funcionando na hora, sem precisar treinar.

Funciona em **Windows, Linux e Mac**.

---

## 1. Baixar o código

Igual em todos os sistemas operacionais:

```bash
git clone https://github.com/fernandacduarte/INF2072
cd INF2072
git checkout capture_v0_pure_potential_shaping
```

## 2. Onboarding (preparar o ambiente)

Requisitos: **Python 3.11** e o **uv**
(instalação: https://docs.astral.sh/uv/getting-started/installation/).

Na pasta do projeto:

```bash
uv sync
```

Isso cria a `.venv` com as dependências exatas travadas em `uv.lock`.

> **Só no Linux/Mac:** o `Makefile` assume por padrão o caminho de Python do
> Windows (`.venv/Scripts/python.exe`). Rode isto **uma vez** na sua sessão de
> terminal para que os alvos `make` usem o Python correto:
>
> ```bash
> export PYTHON=.venv/bin/python
> ```
>
> No Windows não é necessário.

Teste rápido para confirmar que o ambiente está OK:

```bash
make smoke
```

## 3. Reproduzir o resultado na hora (sem treinar)

O checkpoint treinado já está no repositório. Abre uma janela (Pygame)
mostrando os 3 fantasmas capturando o Pac-Man.

**Com GPU (CUDA):**

```bash
make eval-latest
```

**Sem GPU (CPU):** a descoberta automática do melhor run é específica da pasta
do device (o checkpoint versionado está em `.../cuda/`), então numa máquina sem
GPU é preciso apontar o checkpoint explicitamente com `CKPT=`:

```bash
make eval-latest DEVICE=cpu CKPT=benchmarl_setup/runs/pinklike3/capture_v0_closing/cuda/iql_pacman_mlp__884a90e3_26_07_01-03_54_43/checkpoints/checkpoint_1000000.pt
```

**Não tem `make`?** Comandos universais (funcionam em Windows, Linux e Mac):

```bash
# Com GPU:
uv run python custom_environment/eval.py --learner iql --checkpoint-select best --device cuda --maze pinklike3 --reward-id capture_v0_closing --pacman-evasiveness 0.8

# Sem GPU (checkpoint explícito):
uv run python custom_environment/eval.py --learner iql --checkpoint benchmarl_setup/runs/pinklike3/capture_v0_closing/cuda/iql_pacman_mlp__884a90e3_26_07_01-03_54_43/checkpoints/checkpoint_1000000.pt --device cpu --maze pinklike3 --reward-id capture_v0_closing --pacman-evasiveness 0.8
```

> Ambos os caminhos (GPU via descoberta e CPU via `--checkpoint`) foram testados
> a partir de um clone limpo do repositório: os fantasmas capturam o Pac-Man no
> passo ~161 (`Ghosts win`).

## 4. Treinar do zero (opcional, ~1M frames)

```bash
make benchmark ALGOS=iql CHECKPOINT_INTERVAL=100000
```

E, num **segundo terminal**, para acompanhar a curva de recompensa ao vivo:

```bash
make liveplot ALGOS=iql
```

`CHECKPOINT_INTERVAL=100000` gera 10 checkpoints ao longo do treino de 1M frames
(regra geral: nº de checkpoints = `FRAMES / CHECKPOINT_INTERVAL`).

**Sem `make`?** Equivalentes universais:

```bash
uv run python benchmarl_setup/run_benchmark.py --algorithms iql --maze pinklike3 --reward-id capture_v0_closing --max-frames 1000000 --checkpoint-interval 100000 --devices cpu
uv run python benchmarl_setup/liveplot.py --algorithms iql --maze pinklike3 --device all
```

> **Dica:** o benchmark completo roda 5 seeds (validade estatística). Para um
> teste rápido, reduza os frames, por exemplo:
> `make benchmark ALGOS=iql FRAMES=100000 CHECKPOINT_INTERVAL=10000`.

---

## O que esperar

- O melhor run selecionado é o IQL, seed 1, `checkpoint_1000000.pt` (1M frames).
- Taxa de captura reportada: **capture_rate 0.70** (70%).
- Na partida ao vivo, os 3 fantasmas coordenam e capturam o Pac-Man por volta do
  passo ~161 (recompensa terminal grande, ~+101, compartilhada pelos fantasmas).
  As recompensas oscilam passo a passo antes disso (shaping de aproximacao) --
  isso é esperado.

## Notas de compatibilidade

- `uv sync` e `uv run python ...` são idênticos em Windows, Linux e Mac -- por
  isso são o caminho principal e o fallback sem `make`.
- Caminhos de script com `/` (ex.: `custom_environment/eval.py`) funcionam como
  argumento do Python inclusive no Windows.
- `make` no Linux/Mac só precisa do `export PYTHON=.venv/bin/python` (funciona
  porque o `Makefile` usa `?=`, que respeita variável de ambiente).
