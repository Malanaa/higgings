import argparse

from neurostreamlab.evaluation.runner import run_benchmark

parser = argparse.ArgumentParser()
parser.add_argument("config")
parser.add_argument("--force", action="store_true")
args = parser.parse_args()
run_benchmark(args.config, args.force)
