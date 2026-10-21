"""Run historical C2 tests in a disposable copied workspace, preserving originals."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

from plantaox.c2_pu.mcc_study import INTERIM, assert_preserved, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--study', required=True, type=Path)
    args = parser.parse_args()
    study = args.study.resolve()
    root = Path.cwd().resolve()
    # Never overwrite or clean an existing copy; retain it for inspecting failures.
    qa = (INTERIM / 'mcc_improvement_v1' / study.name / 'qa_workspace').resolve()
    qa.mkdir(parents=True, exist_ok=False)
    for name in ('src', 'tests', 'config'):
        shutil.copytree(root / name, qa / name, ignore=shutil.ignore_patterns('__pycache__'))
    for name in ('pyproject.toml', 'requirements.txt', 'README.md'):
        shutil.copy2(root / name, qa / name)
    for stage in ('raw', 'interim', 'processed'):
        shutil.copytree(root / 'data' / stage / 'c2_pu', qa / 'data' / stage / 'c2_pu',
                        ignore=shutil.ignore_patterns('mcc_improvement_v1'))
    env = os.environ.copy()
    env.update(PYTHONPATH=str(qa / 'src'), OMP_NUM_THREADS='1', MKL_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1')
    command = [sys.executable, '-c',
               "import torch,pytest;torch.set_num_threads(1);raise SystemExit(pytest.main(['tests/c2_pu','-q','--tb=short','-p','no:cacheprovider']))"]
    start = time.perf_counter()
    with (study / 'full_suite_isolated.log').open('w', encoding='utf-8') as log:
        result = subprocess.run(command, cwd=qa, env=env, stdout=log, stderr=subprocess.STDOUT)
    write_json(study / 'full_suite_isolated.json', dict(returncode=result.returncode,
               runtime_seconds=time.perf_counter() - start, cwd=str(qa), command=command,
               note='Historical writing tests isolated in copied workspace; WSL availability and Git-disposition portability may fail.'))
    assert_preserved(json.loads((study / 'preservation_before.json').read_text()))
    print((study / 'full_suite_isolated.log').read_text(encoding='utf-8')[-14000:])


if __name__ == '__main__':
    main()
