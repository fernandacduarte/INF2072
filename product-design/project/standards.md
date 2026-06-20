# ENGINEERING STANDARDS — fernanda-INF2072

> Research CLI project. No web backend, no frontend, no database. Standards scoped to Python scripts and testing.

---

## Backend

*N/A — no web framework or ORM. See project structure conventions below.*

### Project Structure

```
benchmarl_setup/
├── run_pacman_benchmarl.py   # Single-algorithm training runner
├── run_benchmark.py          # Multi-seed multi-algorithm benchmark
├── plot_rewards.py           # Reward curve plotting
└── runs/                     # All experiment outputs (gitignored)

custom_environment/
├── pacman_env.py             # PettingZoo AEC environment
├── eval.py                   # Evaluation script
└── render.py                 # Rendering utilities

test/
└── test_*.py                 # Smoke tests
```

### Naming Conventions

| Category | Convention | Examples |
|----------|-----------|---------|
| Modules | `snake_case.py` | `pacman_env.py`, `run_benchmark.py` |
| Classes | `PascalCase` | `PacmanEnv`, `GhostAgent` |
| Functions | `snake_case` | `run_episode`, `compute_reward` |
| Constants | `UPPER_SNAKE_CASE` | `DEFAULT_SEED`, `GHOST_COUNT` |
| CLI args | `--kebab-case` | `--algorithm`, `--seeds` |

### Dependency Management

- `pyproject.toml` + `requirements.txt` per project convention
- Dependencies pinned in `requirements.txt` for reproducible installs
- Python 3.11 required; use `py -3.11` to invoke scripts

### Logging Standards

- Training progress: `print()` to stdout (per-episode reward summary)
- Errors: `sys.stderr` or exception with clear message
- No logging framework required at research-script scale

---

## Frontend

*N/A — no frontend.*

---

## Testing

### Stack

| Tool | Purpose |
|------|---------|
| pytest | Test runner |
| pytest-cov | Coverage reporting |

### Test Location

All tests in `test/`. File naming: `test_<module>.py`.

### Test Patterns

```python
# Environment smoke test
def test_env_step():
    env = PacmanEnv()
    env.reset()
    for agent in env.agent_iter():
        obs, reward, done, truncated, info = env.last()
        action = env.action_space(agent).sample() if not done else None
        env.step(action)
    assert True  # completed without exception
```

### What to Test

- Environment step/reset cycle completes without exception
- Reward shape matches expected structure
- BenchMARL task adapter initializes correctly
- CLI argument parsing accepts valid inputs and rejects invalid ones

### What NOT to Test

- BenchMARL internals (TorchRL framework code)
- PyTorch model weight values
- Rendering output (visual correctness)

### Running Tests

```bash
py -3.11 -m pytest test/
```

---

## i18n

*N/A — English-only CLI tool.*

---

## Security

### Rules

- No API keys or credentials in source code
- PyTorch checkpoints loaded only from local paths specified by the researcher
- Dependencies scanned periodically with `pip-audit`

### Dependency Scanning

```bash
pip-audit
```
