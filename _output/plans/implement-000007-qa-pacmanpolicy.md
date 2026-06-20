# QA Log — implement-000007 | PacmanPolicy BFS safety-aware pellet maximization

**Brief:** implement 000007

---

## Q&A

### Q1: Como rodar os testes neste ambiente?

O `.venv` do projeto (Python 3.11.11) tem numpy/pettingzoo/gymnasium mas **não tem `pytest` nem `pip`**. Os testes foram executados importando cada função `test_*` e chamando-a diretamente pelo interpretador do venv; `test_petting_zoo.py` rodou como script `__main__`. `test_mazes.py` depende de pytest e não pôde ser executado.

**Resultado:** 12/12 testes executáveis passam + PettingZoo `parallel_api_test` (1000 ciclos) passa.

### Q2: Os testes de unidade da policy precisavam de spawns de fantasma?

`parse_layout` exige ao menos um spawn 'G'. Como a `PacmanPolicy` lê posições de fantasmas pelo argumento explícito (não pelas células GHOST do grid), os testes de policy constroem o grid diretamente com numpy (`_open_grid`), evitando a restrição do `parse_layout`.

### Resumo

Plan-000007 implementado em modo manual, 4/4 steps. Pacman agora busca pellets com segurança e foge de fantasmas. Sem regressões.
