"""Usage: detector-golpe vagas.json [mais.json ...]

Each file holds a JSON list of job ads (id, title or name, and any text fields).
Prints one line per ad: id | verdict | signals.
"""

import argparse
import json
import sys
from pathlib import Path

from detector_golpe.rules import analyze, job_from_dict


def main(argv=None):
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(prog="detector-golpe", description="Aponta sinais de golpe em anúncios de vaga.")
    p.add_argument("files", nargs="+", help="arquivos JSON com uma lista de vagas")
    args = p.parse_args(argv)
    jobs = [job_from_dict(o) for f in args.files for o in json.loads(Path(f).read_text(encoding="utf-8"))]
    for r in analyze(jobs):
        print(f"{r['id']} | {r['verdict']} | " + "; ".join(f"{s['code']}: {s['match']}" for s in r["signals"]))
