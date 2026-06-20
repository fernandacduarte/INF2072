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
MAZE   ?= pinklike
GHOSTS ?= 2

.DEFAULT_GOAL := help

.PHONY: help demo demo-ascii demo-clear demo-clear-ascii demo-hard screenshot smoke test

help: ## Show this help
	@$(PYTHON) -c "print('\n'.join(['Pacman MARL demos - available targets:','','  make demo             Live Pygame window (defense-first Pacman vs random ghosts)','  make demo-ascii       Same episode rendered as ASCII in the terminal','  make demo-clear       Live window, runs until every pellet is eaten','  make demo-clear-ascii Clear-the-board run, ASCII (no window)','  make demo-hard        Live window on the default maze for more pressure','  make screenshot       Save a PNG of the last frame to _output/','  make smoke            PettingZoo parallel-API compliance test (no pytest needed)','  make test             Run the pytest suite (requires: pip install pytest)','','Variables: PYTHON DELAY SEED MAZE GHOSTS  (e.g. make demo DELAY=0.2 MAZE=default)']))"

demo: ## Live Pygame window: defense-first Pacman vs random ghosts
	$(PYTHON) custom_environment/render_demo.py --render-mode human --delay $(DELAY) --maze $(MAZE) --number-ghosts $(GHOSTS) --seed $(SEED)

demo-ascii: ## Render an episode as ASCII in the terminal
	$(PYTHON) custom_environment/render_demo.py --render-mode ascii --delay $(DELAY) --maze $(MAZE) --number-ghosts $(GHOSTS) --seed $(SEED)

demo-clear: ## Live window: run until Pacman clears the whole board
	$(PYTHON) custom_environment/run_until_clear.py --render-mode human --delay $(DELAY) --maze $(MAZE) --seed $(SEED)

demo-clear-ascii: ## Clear-the-board run printed to the terminal (no window)
	$(PYTHON) custom_environment/run_until_clear.py --render-mode ascii --delay 0 --maze $(MAZE) --seed $(SEED)

demo-hard: ## Live window on the default maze
	$(PYTHON) custom_environment/render_demo.py --render-mode human --delay $(DELAY) --maze default --number-ghosts $(GHOSTS) --seed $(SEED)

screenshot: ## Save a PNG of the last rendered frame into _output/
	$(PYTHON) custom_environment/render_demo.py --render-mode rgb_array --max-steps 80 --maze $(MAZE) --seed $(SEED) --screenshot-out _output/pacman_demo.png

smoke: ## PettingZoo parallel-API compliance (runs without pytest)
	$(PYTHON) test/test_petting_zoo.py

test: ## Run the pytest suite (requires pytest installed)
	$(PYTHON) -m pytest test/ -v
