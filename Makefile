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
ALGOS   ?= iql,vdn,qmixglobal
SEEDS   ?= 0,1,2,4
FRAMES  ?= 100000
CHECKPOINT_INTERVAL ?= 10000
DEVICE  ?= cuda
REWARD_ID ?= capture_v0_closing
LEARNER ?= qmixglobal
CURRICULUM ?= off
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
PACMAN_RANDOM_ACTION_PROB ?= 0.5
PACMAN_SAFE_DISTANCE ?=
PACMAN_SAFE_DISTANCE_ARG := $(if $(strip $(PACMAN_SAFE_DISTANCE)),--pacman-safe-distance $(PACMAN_SAFE_DISTANCE),)

# Spawn randomization: draw fresh Pacman/ghost cells each episode so the policy
# cannot memorize a fixed route to a fixed start cell and must pursue reactively.
# On by default (1); set RANDOMIZE_SPAWNS=0 to keep the map-authored spawns.
RANDOMIZE_SPAWNS ?= 1
RANDOMIZE_SPAWNS_MIN_DISTANCE ?= 4
RANDOMIZE_SPAWNS_ARG := $(if $(filter-out 0 false no off,$(RANDOMIZE_SPAWNS)),--randomize-spawns,--no-randomize-spawns)

# Capture rule radius (plan-000036). 0 = original co-location-only capture; >0
# enables adjacency capture (ghost within N BFS cells of Pacman counts as a
# capture). Changes the task definition -- re-baseline; never mix radii in a plot.
#   make benchmark CAPTURE_RADIUS=1
CAPTURE_RADIUS ?= 0

# Scripted-pursuit capture-ceiling diagnostic (plan-000036). Measures the upper
# bound capture rate a near-optimal (untrained) ghost team reaches, to tell a
# learning gap from a structural ceiling.
CEILING_DIFFICULTY ?= hard
CEILING_EPISODES   ?= 40
CEILING_SEEDS      ?= 0,1,2,3,4

.DEFAULT_GOAL := help

# R1 positive-control sanity battery knobs (plan-000034 / research-000032).
# Decides whether the ~40% capture ceiling "against a random Pacman" is a
# confound or a genuine learning limit BEFORE any hyperparameter sweep.
R1_ALGOS         ?= iql,vdn,qmixglobal
R1_SEEDS         ?= 0,1,2,3,4
R1_FRAMES        ?= 60000
R1_EVAL_EPISODES ?= 40
R1_SAVE          ?= benchmarl_setup/runs/r1

.PHONY: help demo demo-ascii demo-clear demo-clear-ascii demo-hard screenshot smoke test benchmark liveplot eval-best r1-positive-control ceiling

help: ## Show this help
	@$(PYTHON) -c "print('\n'.join(['Pacman MARL demos - available targets:','','  make demo             Live Pygame window (defense-first Pacman vs random ghosts)','  make demo-ascii       Same episode rendered as ASCII in the terminal','  make demo-clear       Live window, runs until every pellet is eaten','  make demo-clear-ascii Clear-the-board run, ASCII (no window)','  make demo-hard        Live window on the default maze for more pressure','  make screenshot       Save a PNG of the last frame to _output/','  make benchmark        Multi-seed reward/algorithm benchmark matrix','  make ceiling          Scripted-pursuit capture-ceiling diagnostic (no training)','  make r1-positive-control  R1 sanity battery: random opponent vs curriculum + verdict','  make liveplot         Live mean+/-std reward monitor (run in a second terminal)','  make eval-best        Watch trained ghosts (best checkpoint) in a Pygame window','  make smoke            PettingZoo parallel-API compliance test (no pytest needed)','  make test             Run the pytest suite (requires: pip install pytest)','','Demo vars: PYTHON DELAY SEED MAZE         (e.g. make demo DELAY=0.2 MAZE=default)','Bench vars: ALGOS SEEDS FRAMES MAZE DEVICE REWARD_ID CURRICULUM EPSILON_ANNEAL_RATIO','            PACMAN_DIFFICULTY PACMAN_RANDOM_ACTION_PROB PACMAN_SAFE_DISTANCE','            RANDOMIZE_SPAWNS RANDOMIZE_SPAWNS_MIN_DISTANCE','            (dumber Pacman: make benchmark CURRICULUM=off PACMAN_DIFFICULTY=easy)','            (stabler curve: make benchmark EPSILON_ANNEAL_RATIO=0.5)','            (fixed spawns: make benchmark RANDOMIZE_SPAWNS=0)','            (adjacency capture: make benchmark CAPTURE_RADIUS=1)','Ceiling vars: MAZE CEILING_DIFFICULTY CEILING_EPISODES CEILING_SEEDS CAPTURE_RADIUS','Eval vars:  LEARNER DEVICE REWARD_ID']))"

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
	$(PYTHON) benchmarl_setup/run_benchmark.py --algorithms $(ALGOS) --reward-ids $(REWARD_ID) --seeds $(SEEDS) --max-frames $(FRAMES) --maze $(MAZE) --devices $(DEVICE) --checkpoint-interval $(CHECKPOINT_INTERVAL) --pacman-curriculum $(CURRICULUM) --pacman-curriculum-max-frames $(CURRICULUM_MAX_FRAMES) --pacman-difficulty $(PACMAN_DIFFICULTY) --pacman-random-action-prob $(PACMAN_RANDOM_ACTION_PROB) $(PACMAN_SAFE_DISTANCE_ARG) --epsilon-anneal-ratio $(EPSILON_ANNEAL_RATIO) $(RANDOMIZE_SPAWNS_ARG) --randomize-spawns-min-distance $(RANDOMIZE_SPAWNS_MIN_DISTANCE) --capture-radius $(CAPTURE_RADIUS)

ceiling: ## Scripted-pursuit capture-ceiling diagnostic vs the configured Pacman
	$(PYTHON) custom_environment/ceiling_eval.py --maze $(MAZE) --pacman-difficulty $(CEILING_DIFFICULTY) --episodes $(CEILING_EPISODES) --seeds $(CEILING_SEEDS) --capture-radius $(CAPTURE_RADIUS)


r1-positive-control: ## R1 sanity battery: random opponent (P) vs curriculum (C), then print the verdict
	$(PYTHON) benchmarl_setup/run_r1_positive_control.py --algorithms $(R1_ALGOS) --seeds $(R1_SEEDS) --max-frames $(R1_FRAMES) --eval-episodes $(R1_EVAL_EPISODES) --maze $(MAZE) --devices $(DEVICE) --save-folder $(R1_SAVE)
	$(PYTHON) benchmarl_setup/summarize_r1.py --p-folder $(R1_SAVE)/condition_P --c-folder $(R1_SAVE)/condition_C

liveplot: ## Live mean+/-std reward monitor (run in a second terminal during a benchmark)
	$(PYTHON) benchmarl_setup/liveplot.py --algorithms $(ALGOS) --maze $(MAZE) --device all

plot:
	$(PYTHON) benchmarl_setup/plot_benchmarl_reward.py --algorithms $(ALGOS) --maze $(MAZE) --device $(DEVICE) --reward-id $(REWARD_ID)

smoke: ## PettingZoo parallel-API compliance (runs without pytest)
	$(PYTHON) test/test_petting_zoo.py

test: ## Run the pytest suite (requires pytest installed)
	$(PYTHON) -m pytest test/ -v
