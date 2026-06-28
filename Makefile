# Makefile — Pacman MARL demos and checks
#
# Uses the project's .venv interpreter by default (it has numpy, pettingzoo,
# gymnasium and pygame installed). Override any variable on the command line,
# e.g.:  make demo DELAY=0.2 MAZE=default SEED=7
#
# On Windows the .venv python is at .venv/Scripts/python.exe; on Linux/macOS
# override with  make demo PYTHON=.venv/bin/python

PYTHON ?= py -3.11
DELAY  ?= 0.12
SEED   ?= 11
MAZE   ?= pinklike3

# Benchmark training knobs (override on the command line, e.g. make benchmark FRAMES=1200)
ALGOS   ?= qmixglobal
SEEDS   ?= 0
FRAMES  ?= 10000
CHECKPOINT_INTERVAL ?= 2000
DEVICE  ?= cuda
REWARD_ID ?= capture_v0_improve_legal_moves_increase_terminal_rewards_reverse_action
LEARNER ?= qmixglobal
CURRICULUM ?= easy-medium-hard
CURRICULUM_MAX_FRAMES ?= $(FRAMES)

.DEFAULT_GOAL := help

.PHONY: help demo demo-ascii demo-clear demo-clear-ascii demo-hard screenshot smoke test benchmark liveplot eval-best

help: ## Show this help
	@$(PYTHON) -c "print('\n'.join(['Pacman MARL demos - available targets:','','  make demo             Live Pygame window (defense-first Pacman vs random ghosts)','  make demo-ascii       Same episode rendered as ASCII in the terminal','  make demo-clear       Live window, runs until every pellet is eaten','  make demo-clear-ascii Clear-the-board run, ASCII (no window)','  make demo-hard        Live window on the default maze for more pressure','  make screenshot       Save a PNG of the last frame to _output/','  make benchmark        Multi-seed reward/algorithm benchmark matrix','  make liveplot         Live mean+/-std reward monitor (run in a second terminal)','  make eval-best        Watch trained ghosts (best checkpoint) in a Pygame window','  make smoke            PettingZoo parallel-API compliance test (no pytest needed)','  make test             Run the pytest suite (requires: pip install pytest)','','Demo vars: PYTHON DELAY SEED MAZE         (e.g. make demo DELAY=0.2 MAZE=default)','Bench vars: ALGOS SEEDS FRAMES MAZE DEVICE REWARDS','Eval vars:  LEARNER DEVICE REWARD_ID']))"

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
	$(PYTHON) custom_environment/eval.py --learner $(LEARNER) --checkpoint-select latest --device $(DEVICE) --maze $(MAZE) --reward-id $(REWARD_ID)

benchmark: ## Multi-seed benchmark training (parallel algorithms, serial seeds)
	$(PYTHON) benchmarl_setup/run_benchmark.py --algorithms $(ALGOS) --reward-ids $(REWARD_ID) --seeds $(SEEDS) --max-frames $(FRAMES) --maze $(MAZE) --devices $(DEVICE) --checkpoint-interval $(CHECKPOINT_INTERVAL) --pacman-curriculum $(CURRICULUM) --pacman-curriculum-max-frames $(CURRICULUM_MAX_FRAMES)


liveplot: ## Live mean+/-std reward monitor (run in a second terminal during a benchmark)
	$(PYTHON) benchmarl_setup/liveplot.py --algorithms $(ALGOS) --maze $(MAZE) --device all

plot:
	$(PYTHON) benchmarl_setup/plot_benchmarl_reward.py --algorithms $(ALGOS) --maze $(MAZE) --device $(DEVICE) --reward-id $(REWARD_ID)

smoke: ## PettingZoo parallel-API compliance (runs without pytest)
	$(PYTHON) test/test_petting_zoo.py

test: ## Run the pytest suite (requires pytest installed)
	$(PYTHON) -m pytest test/ -v
