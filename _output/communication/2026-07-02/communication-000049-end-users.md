# Communication 000049 | USR | 2026-07-02 00:00 UTC | End Users

# Guia pratico: reproduza a avaliacao dos fantasmas treinados

Este guia mostra, passo a passo, como um colega reproduzir na propria maquina o resultado recente de avaliacao do nosso ambiente Pacman multi-agente. Ao final voce tera:

1. Assistido aos 3 fantasmas treinados coordenarem e capturarem o Pacman em uma partida ao vivo.
2. Reproduzido o mesmo numero relatado de taxa de captura (capture_rate 0.70).
3. Aprendido a abrir o monitor de recompensa ao vivo (liveplot) com exatamente 10 checkpoints durante um treino.

Publico: colegas de pos-graduacao com familiaridade em Python e RL, mas talvez novos neste repositorio. Todos os comandos abaixo sao executados a partir da raiz do projeto.

---

## O que voce vai reproduzir

O ambiente e um Pacman customizado onde os fantasmas sao agentes cooperativos: eles compartilham uma unica recompensa de time e precisam coordenar para encurralar o Pacman. A configuracao alvo deste guia e:

- Labirinto: `pinklike3` (variante com 3 spawns de fantasma, ou seja, 3 fantasmas cooperativos).
- Estrategia de recompensa: `capture_v0_closing` (recompensa de aproximacao persistente que premia reduzir a distancia ate o Pacman a cada passo, mais o bonus grande de captura no final).
- Algoritmo: IQL.

---

## Pre-requisitos

- Sistema operacional: Windows (os comandos usam o interpretador `.venv/Scripts/python.exe`).
- Python 3.11 e obrigatorio. Verifique com:

  ```bash
  py -3.11 --version
  ```

- GPU (CUDA) foi usada na execucao de referencia (`--device cuda`). Nao ter GPU nao e impedimento: tudo funciona em CPU trocando `--device cuda` por `--device cpu` (veja Solucao de problemas no final).

---

## Passo 1 - Preparar o ambiente

1. Crie o ambiente virtual com Python 3.11 (uma unica vez):

   ```bash
   py -3.11 -m venv venv
   ```

2. Ative o ambiente virtual (Windows PowerShell):

   ```bash
   .\venv\Scripts\Activate.ps1
   ```

   Ou, no Prompt de Comando (cmd):

   ```bash
   venv\Scripts\activate
   ```

3. Instale as dependencias:

   ```bash
   pip install -r requirements.txt
   ```

Observacao sobre o interpretador: os comandos deste guia (e o Makefile) usam o caminho `.venv/Scripts/python.exe`. Se o seu ambiente virtual se chama `venv` em vez de `.venv`, use `venv\Scripts\python.exe` ou execute os comandos explicitos abaixo trocando o caminho do Python.

---

## Passo 2 - Reproduzir a avaliacao (assistir aos fantasmas treinados)

A forma mais simples e usar o atalho do Makefile:

```bash
make eval-latest
```

Esse atalho executa exatamente o comando abaixo. Se voce preferir rodar sem o `make`, use a versao explicita:

```bash
.venv/Scripts/python.exe custom_environment/eval.py --learner iql --checkpoint-select best --device cuda --maze pinklike3 --reward-id capture_v0_closing --pacman-evasiveness 0.8
```

O que cada parte significa:

- `--checkpoint-select best`: seleciona automaticamente a melhor execucao pela taxa de captura, entao voce nao precisa apontar o arquivo do checkpoint manualmente.
- `--pacman-evasiveness 0.8`: define um Pacman dificil. Isso corresponde a uma probabilidade de acao aleatoria de 0.2 (ou seja, o Pacman age de forma evasiva em 80% dos passos).
- `--maze pinklike3` e `--reward-id capture_v0_closing`: garantem que a avaliacao leia da subpasta correta de resultados.

Uma janela do Pygame abre e roda uma partida completa controlada pela politica treinada.

---

## Passo 3 - Resultado esperado e como interpretar

Antes da partida comecar, o `eval.py` imprime a estatistica do checkpoint selecionado. Voce deve ver algo consistente com:

- Melhor execucao selecionada: `iql_pacman_mlp__884a90e3_...`, seed 1, checkpoint `checkpoint_1000000.pt` (isto e, apos 1.000.000 de frames de treino).
- Metrica relatada: capture_rate = 0.70 (70%). matched_runs 4/4.

Na partida ao vivo:

- Os 3 fantasmas coordenam e capturam o Pacman por volta do passo ~161.
- No momento da captura ha uma recompensa terminal grande e positiva (cerca de +101) compartilhada por todos os fantasmas.
- Antes da captura, as recompensas oscilam de passo para passo. Isso e esperado: a estrategia `capture_v0_closing` da recompensa por aproximacao (fechar a distancia), entao o sinal sobe e desce conforme os fantasmas manobram. Nao interprete essa oscilacao como falha; o indicador de sucesso e a captura no final.

Onde ficam os resultados: as saidas vivem sob `benchmarl_setup/runs/pinklike3/capture_v0_closing/<device>/` (por exemplo, `cuda` ou `cpu` conforme o dispositivo que voce usou).

Como saber que deu certo:

- A janela final mostra o desfecho da partida (vitoria dos fantasmas) com o numero de passos, a recompensa do time e o tempo decorrido.
- O numero de capture_rate impresso antes da partida deve bater com 0.70.

---

## Passo 4 - Reproduzir o liveplot com exatamente 10 checkpoints

O `make liveplot` abre um monitor ao vivo da recompensa media (com banda de desvio padrao). Ele foi feito para rodar em um SEGUNDO terminal ENQUANTO um benchmark treina, pois ele fica lendo o arquivo de progresso do treino em andamento.

O comando que ele executa por baixo e:

```bash
python benchmarl_setup/liveplot.py --algorithms iql --maze pinklike3 --device all
```

### A regra dos checkpoints

O numero de checkpoints gerados durante o treino segue uma regra simples:

```text
numero de checkpoints = FRAMES / CHECKPOINT_INTERVAL
```

Para obter exatamente 10 checkpoints, basta definir o intervalo de checkpoint como `FRAMES / 10`. Com o padrao de 1.000.000 de frames, isso da `CHECKPOINT_INTERVAL=100000`, produzindo checkpoints em 100k, 200k, ... ate 1M frames (10 pontos igualmente espacados).

### Como rodar (dois terminais)

Terminal 1 - inicie o benchmark com o intervalo ajustado para 10 checkpoints:

```bash
make benchmark ALGOS=iql MAZE=pinklike3 REWARD_ID=capture_v0_closing FRAMES=1000000 CHECKPOINT_INTERVAL=100000
```

Terminal 2 - logo em seguida, abra o monitor ao vivo:

```bash
make liveplot ALGOS=iql MAZE=pinklike3
```

Isso gera 10 checkpoints igualmente espacados e uma curva ao vivo que se atualiza conforme o treino avanca.

### Versao mais rapida e barata (ainda 10 checkpoints)

Um treino de 1.000.000 de frames leva bastante tempo. Para uma demonstracao mais rapida, reduza os frames e mantenha a regra `CHECKPOINT_INTERVAL = FRAMES / 10`. Por exemplo, com 100.000 frames:

```bash
make benchmark ALGOS=iql MAZE=pinklike3 REWARD_ID=capture_v0_closing FRAMES=100000 CHECKPOINT_INTERVAL=10000
```

Isso ainda produz 10 checkpoints, so que muito mais rapido. Lembre-se: um treino curto nao vai atingir a mesma qualidade do resultado de referencia (que usou 1M de frames); use a versao curta apenas para ver o mecanismo do liveplot funcionando.

---

## Solucao de problemas

CPU em vez de CUDA. Se voce nao tem GPU ou o CUDA nao esta disponivel, troque `--device cuda` por `--device cpu` no comando explicito, ou passe `DEVICE=cpu` para os atalhos do make:

```bash
make eval-latest DEVICE=cpu
```

Os resultados passam a ficar sob a subpasta `cpu` (por exemplo `benchmarl_setup/runs/pinklike3/capture_v0_closing/cpu/`).

Caminho do interpretador (venv). O Makefile assume o interpretador em `.venv/Scripts/python.exe`. Se o seu ambiente virtual se chama `venv`, ajuste o comando explicito para `venv\Scripts\python.exe`, ou informe o caminho ao make com a variavel `PYTHON`:

```bash
make eval-latest PYTHON=venv/Scripts/python.exe
```

Versao errada do Python. Se algo falhar na instalacao ou na importacao das bibliotecas, confirme que voce esta em Python 3.11 com `py -3.11 --version` e que o ambiente virtual foi criado com essa versao.

Nao encontra o checkpoint. A selecao `--checkpoint-select best` procura pela melhor execucao no dispositivo indicado. Se voce treinou em CPU mas avaliou pedindo `--device cuda` (ou vice-versa), a avaliacao vai olhar a subpasta errada. Use o mesmo dispositivo no treino e na avaliacao, ou ajuste `DEVICE=` de acordo.

---

Fonte de verdade dos comandos: `README.md` e `Makefile` do projeto. Todos os comandos deste guia sao os mesmos definidos nesses arquivos.
