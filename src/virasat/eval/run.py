import argparse


def main() -> None:
    parser = argparse.ArgumentParser(prog="eval")
    parser.add_argument("--gate", action="store_true", help="exit non-zero on a real gate failure")
    parser.parse_args()
    # No labelled data exists yet; the harness (plan step S7) reports BLOCKED
    # rather than a number it did not compute.
    print("eval: BLOCKED — no labelled data on disk; no metrics computed")
