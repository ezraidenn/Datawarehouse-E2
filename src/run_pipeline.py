"""Run the pipeline: RAW -> CLEAN -> SPATIAL JOIN -> POSTGRESQL DW.

Usage:
    python -m src.run_pipeline                 # every stage
    python -m src.run_pipeline --stage clean   # one stage: clean | join | load

Raw files must already be present (python -m src.download).
"""

from __future__ import annotations

import argparse
import sys
import time

from src import (clean_census, clean_crime, clean_crime_municipal, clean_denue, clean_geography,
                 config, extract_crime, load_dw, spatial_join)

STAGES = ("clean", "join", "load")


def stage_clean() -> None:
    config.DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    clean_geography.main()
    clean_census.main()
    clean_denue.main()
    try:
        extract_crime.main()
    except FileNotFoundError as error:
        print(f"crime: {error}")
        extract_crime.OUTPUT.unlink(missing_ok=True)
    clean_crime.main()
    clean_crime_municipal.main()


def stage_join() -> None:
    spatial_join.main()


def stage_load() -> int:
    return load_dw.main()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--stage", choices=STAGES, help="run only this stage")
    args = parser.parse_args()

    status = 0
    for stage in STAGES:
        if args.stage and stage != args.stage:
            continue
        started = time.perf_counter()
        print(f"== {stage}")
        if stage == "clean":
            stage_clean()
        elif stage == "join":
            stage_join()
        else:
            status = stage_load()
        print(f"== {stage} finished in {time.perf_counter() - started:.1f}s")
        if status:
            break
    return status


if __name__ == "__main__":
    sys.exit(main())
