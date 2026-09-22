"""Create a factorial iteration/batch grid without changing the other parameters."""
import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, nargs="+", default=[50, 200])
    parser.add_argument("--batches", type=int, nargs="+", default=[4, 10])
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    variants = []
    for provider in ("qaia", "greedy"):
        for iterations in (args.iterations if provider == "qaia" else [200]):
            for batch in args.batches:
                variants.append(dict(
                    name=f"{provider}_{iterations}_{batch}" if provider == "qaia" else f"greedy_{batch}",
                    env=dict(QAIA_PROVIDER=provider, QAIA_N_ITER=str(iterations),
                        QAIA_BATCH_SIZE=str(batch), QAIA_DT="1.0", QAIA_MAX_COLUMNS="3",
                        QAIA_MAX_STREAK="3", QAIA_COLUMN_POLICY="combined",
                        QAIA_EXACT_MODE="on_qaia_failure")))
    path = Path(args.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(variants, stream, indent=2)


if __name__ == "__main__":
    main()
