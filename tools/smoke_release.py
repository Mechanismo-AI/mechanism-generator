"""Verify released weights through the public CLI and one small real solver run."""
import argparse
import csv
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from mechanism_generator.engine.models import verify


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models-directory", type=Path, required=True)
    args = parser.parse_args()
    models = args.models_directory.resolve()
    verify(models)
    with tempfile.TemporaryDirectory(prefix="mg-smoke-") as work:
        output = Path(work) / "results"
        env = dict(os.environ, OMP_NUM_THREADS="1", MKL_NUM_THREADS="1", MPLCONFIGDIR=str(Path(work) / "mpl"))
        command = [sys.executable, "-m", "mechanism_generator.engine", "--models-directory", str(models),
                   "--targets", "-6", "2", "-2", "6", ".5", "3.5", "--quick", "--branches", "both",
                   "--device", "cpu", "--headless", "--no_plots", "--strict_qualification",
                   "--portfolio_guarantee_fixed_count", "0", "--output_root", str(output)]
        subprocess.run(command, cwd=work, env=env, check=True, timeout=300)
        manifests = list(output.rglob("run_manifest.json"))
        assert len(manifests) == 1
        manifest = json.loads(manifests[0].read_text())
        assert len(manifest["models"]) == 3 and len(manifest["targets"]) == 1
        for selected in output.rglob("selected_candidates.csv"):
            with selected.open(newline="") as stream:
                assert all(row["selection_eligible"] == "True" for row in csv.DictReader(stream))
        for record in output.rglob("*.json"):
            assert work not in record.read_text(), "Machine-specific output root leaked into a saved report"
        print("Release weights passed CLI execution and qualification/path-record checks.")


if __name__ == "__main__":
    main()
