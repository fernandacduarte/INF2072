# Makefile — Pacman MARL demos and checks
#
# Uses the project's .venv interpreter by default (it has numpy, pettingzoo,
# gymnasium and pygame installed). Override any variable on the command line,
# e.g.:  make demo DELAY=0.2 MAZE=default SEED=7
#
# On Windows the .venv python is at .venv/Scripts/python.exe; on Linux/macOS
# override with  make demo PYTHON=.venv/bin/python

PYTHON ?= .venv/Scripts/python.exe
DELAY  ?= 0.12
SEED   ?= 11
MAZE   ?= pinklike3

# Benchmark training knobs (override on the command line, e.g. make benchmark FRAMES=1200)
ALGOS   ?= qmixglobal
SEEDS   ?= 0,1,2
FRAMES  ?= 300000
CHECKPOINT_INTERVAL ?= 10000
DEVICE  ?= cuda
REWARD_ID ?= capture_v0_pure_potential_shaping
LEARNER ?= qmixglobal
CURRICULUM ?= easy-medium-hard
CURRICULUM_MAX_FRAMES ?= $(FRAMES)
# Fraction of training over which exploration epsilon anneals 1.0 -> 0.1.
# Lower (e.g. 0.5) gives the greedy policy a longer low-epsilon phase to
# converge and stabilizes the capture-rate curve. Upstream default is 0.95.
EPSILON_ANNEAL_RATIO ?= 0.5

# Pacman difficulty knobs (make the prey dumber to bootstrap ghost pursuit).
# NOTE: PACMAN_DIFFICULTY and PACMAN_RANDOM_ACTION_PROB only take effect when
# CURRICULUM=off; with a curriculum the easy->medium->hard schedule sets these
# per stage. Eval always forces a hard Pacman regardless of these (by design).
#   Dumbest:   make benchmark CURRICULUM=off PACMAN_DIFFICULTY=easy
#   Noisy:     make benchmark CURRICULUM=off PACMAN_RANDOM_ACTION_PROB=0.5
PACMAN_DIFFICULTY ?= hard
PACMAN_RANDOM_ACTION_PROB ?= 0.0
PACMAN_SAFE_DISTANCE ?=
PACMAN_SAFE_DISTANCE_ARG := $(if $(strip $(PACMAN_SAFE_DISTANCE)),--pacman-safe-distance $(PACMAN_SAFE_DISTANCE),)

.DEFAULT_GOAL := help

.PHONY: help demo demo-ascii demo-clear demo-clear-ascii demo-hard screenshot smoke test benchmark liveplot eval-best

help: ## Show this help
	@$(PYTHON) -c "print('\n'.join(['Pacman MARL demos - available targets:','','  make demo             Live Pygame window (defense-first Pacman vs random ghosts)','  make demo-ascii       Same episode rendered as ASCII in the terminal','  make demo-clear       Live window, runs until every pellet is eaten','  make demo-clear-ascii Clear-the-board run, ASCII (no window)','  make demo-hard        Live window on the default maze for more pressure','  make screenshot       Save a PNG of the last frame to _output/','  make benchmark        Multi-seed reward/algorithm benchmark matrix','  make liveplot         Live mean+/-std reward monitor (run in a second terminal)','  make eval-best        Watch trained ghosts (best checkpoint) in a Pygame window','  make smoke            PettingZoo parallel-API compliance test (no pytest needed)','  make test             Run the pytest suite (requires: pip install pytest)','','Demo vars: PYTHON DELAY SEED MAZE         (e.g. make demo DELAY=0.2 MAZE=default)','Bench vars: ALGOS SEEDS FRAMES MAZE DEVICE REWARD_ID CURRICULUM EPSILON_ANNEAL_RATIO','            PACMAN_DIFFICULTY PACMAN_RANDOM_ACTION_PROB PACMAN_SAFE_DISTANCE','            (dumber Pacman: make benchmark CURRICULUM=off PACMAN_DIFFICULTY=easy)','            (stabler curve: make benchmark EPSILON_ANNEAL_RATIO=0.5)','Eval vars:  LEARNER DEVICE REWARD_ID']))"

demo: ## Live Pygame window: defense-first Pacman vs random ghosts
	$(PYTHON) custom_environment/render_demo.py --render-mode human --delay $(DELAY) --maze $(MAZE) --seed $(SEED)

demo-ascii: ## Render an episode as ASCII in the terminal
	$(PYTHON) custom_environment/render_demo.py --render-mode ascii --delay $(DELAY) --maze $(MAZE) --seed $(SEED)

demo-clear: ## Live window: run until Pacman clears the whole board
	$(PYTHON) custom_environment/run_until_clear.py --render-mode human --delay $(DELAY) --maze $(MAZE) --seed $(SEED)

demo-clear-ascii: ## Clear-the-board run printed to the terminal (no window)
	$(PYTHON) custom_environment/run_until_clear.py --render-mode ascii --delay 0 --maze $(MAZE) --seed $(SEED)

demo-hard: ## Live window on the default maze
	$(PYTHON) custom_environment/render_demo.py --render-mode human --delay $(DELAY) --maze default --seed $(SEED)

screenshot: ## Save a PNG of the last rendered frame into _output/
	$(PYTHON) custom_environment/render_demo.py --render-mode rgb_array --max-steps 80 --maze $(MAZE) --seed $(SEED) --screenshot-out _output/pacman_demo.png

eval-latest: ## Watch trained ghosts (latest checkpoint) in a Pygame window
	$(PYTHON) custom_environment/eval.py --learner $(LEARNER) --checkpoint-select best --device $(DEVICE) --maze $(MAZE) --reward-id $(REWARD_ID)

benchmark: ## Multi-seed benchmark training (parallel algorithms, serial seeds)
	$(PYTHON) benchmarl_setup/run_benchmark.py --algorithms $(ALGOS) --reward-ids $(REWARD_ID) --seeds $(SEEDS) --max-frames $(FRAMES) --maze $(MAZE) --devices $(DEVICE) --checkpoint-interval $(CHECKPOINT_INTERVAL) --pacman-curriculum $(CURRICULUM) --pacman-curriculum-max-frames $(CURRICULUM_MAX_FRAMES) --pacman-difficulty $(PACMAN_DIFFICULTY) --pacman-random-action-prob $(PACMAN_RANDOM_ACTION_PROB) $(PACMAN_SAFE_DISTANCE_ARG) --epsilon-anneal-ratio $(EPSILON_ANNEAL_RATIO)


liveplot: ## Live mean+/-std reward monitor (run in a second terminal during a benchmark)
	$(PYTHON) benchmarl_setup/liveplot.py --algorithms $(ALGOS) --maze $(MAZE) --device all

smoke: ## PettingZoo parallel-API compliance (runs without pytest)
	$(PYTHON) test/test_petting_zoo.py

test: ## Run the pytest suite (requires pytest installed)
	$(PYTHON) -m pytest test/ -v
