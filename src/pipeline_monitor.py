"""pipeline_monitor.py
~~~~~~~~~~~~~~~~~~~~~~

CareerLens pipeline monitoring utilities.

This module provides lightweight wrappers around the existing ingestion and
validation scripts.  It records execution time, basic record counts and
validation outcomes, and returns a **single JSON‑serialisable** dictionary
that can be printed or written to a log file.

The implementation purposefully **does not modify** any of the original
pipeline logic – it simply imports the functions and captures their return
values (or derives simple metrics when the original function returns ``None``).
"""

import json
import time
import os
from pathlib import Path

# Import existing pipeline components.  The imports are relative to the
# ``src`` package, which is on the Python path when this module is executed
# from the repository root (``python -m src.pipeline_monitor``).
from src import ingestion
from src import incremental_ingestion
from src import validation

# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    """Return the current time as an ISO‑8601 string with timezone info."""
    return time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime())


def _duration_seconds(start: float, end: float) -> float:
    """Calculate elapsed seconds with two‑decimal precision."""
    return round(end - start, 2)

# ---------------------------------------------------------------------------
# Monitoring wrappers
# ---------------------------------------------------------------------------

def monitor_full_ingestion() -> dict:
    """Run the *full* ingestion (``src.ingestion.ingest_data``).

    The original ``ingest_data`` function writes a JSON file with the raw API
    response but does not return a value.  This wrapper captures the start/end
    timestamps, reads the generated file to compute the record count and file
    size, and reports a ``PASS``/``FAIL`` flag based on the function's exit
    status (non‑zero exit would raise ``SystemExit`` – we treat that as a
    failure).
    """
    start = time.time()
    try:
        ingestion.ingest_data()
        status = "PASS"
    except SystemExit:
        status = "FAIL"
    end = time.time()

    # The raw file location is defined in ``src.ingestion`` as ``OUTPUT_PATH``.
    raw_path = Path(ingestion.OUTPUT_PATH)
    if raw_path.is_file():
        # Load the JSON to count the ``data`` array length.
        try:
            with raw_path.open("r", encoding="utf-8") as f:
                raw_json = json.load(f)
            records = raw_json.get("data", []) if isinstance(raw_json, dict) else []
            record_count = len(records)
        except Exception:
            record_count = None
        file_size_mb = round(raw_path.stat().st_size / (1024 * 1024), 2)
    else:
        record_count = None
        file_size_mb = None

    return {
        "pipeline": "full_ingestion",
        "timestamp": _now_iso(),
        "elapsed_seconds": _duration_seconds(start, end),
        "status": status,
        "metrics": {
            "record_count": record_count,
            "raw_file_path": str(raw_path),
            "raw_file_size_mb": file_size_mb,
        },
    }


def monitor_incremental_ingestion(api_records=None, is_test_mode: bool = False) -> dict:
    """Run the incremental ingestion pipeline and capture its summary.

    ``src.incremental_ingestion.run_incremental_pipeline`` already returns a
    dictionary with the important counts (inserted, updated, skipped, etc.).
    This wrapper augments that result with timing information and a high‑level
    ``PASS``/``FAIL`` flag – the pipeline is considered ``PASS`` when the
    function completes without raising an exception.
    """
    start = time.time()
    try:
        result = incremental_ingestion.run_incremental_pipeline(
            api_records=api_records, is_test_mode=is_test_mode
        )
        status = "PASS"
    except Exception as e:
        # Capture the exception message for debugging.
        result = {"error": str(e)}
        status = "FAIL"
    end = time.time()

    # Ensure the required keys exist even if the pipeline failed early.
    base_metrics = {
        "batch_size": result.get("batch_size"),
        "inserted": result.get("inserted"),
        "updated": result.get("updated"),
        "skipped": result.get("skipped"),
        "initial_count": result.get("initial_count"),
        "final_count": result.get("final_count"),
    }

    return {
        "pipeline": "incremental_ingestion",
        "timestamp": _now_iso(),
        "elapsed_seconds": _duration_seconds(start, end),
        "status": status,
        "metrics": base_metrics,
    }


def monitor_validation(file_path: str = "data/processed/jobs_clean.csv") -> dict:
    """Execute the validation script and return its outcome.

    The ``validate_dataset`` function already returns a dictionary containing a
    ``status`` key (``PASS``/``FAIL``) and a ``results`` DataFrame.  We serialise
    the DataFrame to a list of dicts for JSON friendliness.
    """
    start = time.time()
    try:
        result = validation.validate_dataset(file_path=file_path)
        status = result.get("status", "FAIL")
        # Convert the DataFrame (if present) to nested JSON.
        results_df = result.get("results")
        if hasattr(results_df, "to_dict"):
            results_serialised = results_df.to_dict(orient="records")
        else:
            results_serialised = None
    except SystemExit:
        # ``validate_dataset`` exits with ``sys.exit(1)`` on failure.
        status = "FAIL"
        result = {}
        results_serialised = None
    except Exception as e:
        status = "FAIL"
        result = {"error": str(e)}
        results_serialised = None
    end = time.time()

    return {
        "pipeline": "validation",
        "timestamp": _now_iso(),
        "elapsed_seconds": _duration_seconds(start, end),
        "status": status,
        "metrics": {
            "file_path": file_path,
            "validation_results": results_serialised,
            **{k: v for k, v in result.items() if k not in ["results", "status"]},
        },
    }


def monitor_naukri_incremental(raw_file_path=None):
    """Run the Naukri incremental ingestion (adapter + SQL MERGE) and capture metrics.

    The function imports ``src.ingest_naukri_incremental.ingest_naukri_batch`` which
    returns a dictionary with batch size and insert/update/skip counts.  This wrapper
    adds timing information and a high‑level PASS/FAIL flag.
    """
    start = time.time()
    try:
        # Import locally to avoid circular import at module load time.
        from src.ingest_naukri_incremental import ingest_naukri_batch
        result = ingest_naukri_batch(raw_file_path=raw_file_path)
        status = "PASS"
    except Exception as e:
        result = {"error": str(e)}
        status = "FAIL"
    end = time.time()

    # Ensure expected keys exist even on failure.
    base_metrics = {
        "batch_size": result.get("batch_size"),
        "inserted": result.get("inserted"),
        "updated": result.get("updated"),
        "skipped": result.get("skipped"),
        "initial_count": result.get("initial_count"),
        "final_count": result.get("final_count"),
    }

    return {
        "pipeline": "naukri_incremental",
        "timestamp": _now_iso(),
        "elapsed_seconds": _duration_seconds(start, end),
        "status": status,
        "metrics": base_metrics,
    }


# ---------------------------------------------------------------------------
# Command‑line interface
# ---------------------------------------------------------------------------

def _print_json(data: dict):
    """Pretty‑print a dictionary as JSON to STDOUT."""
    print(json.dumps(data, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="CareerLens pipeline monitor")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("full", help="Run full ingestion and report metrics")
    subparsers.add_parser("incremental", help="Run incremental ingestion and report metrics")
    parser_val = subparsers.add_parser("validate", help="Run dataset validation")
    parser_val.add_argument(
        "--file",
        default="data/processed/jobs_clean.csv",
        help="Path to the processed CSV file to validate",
    )

    args = parser.parse_args()

    if args.command == "full":
        _print_json(monitor_full_ingestion())
    elif args.command == "incremental":
        _print_json(monitor_incremental_ingestion())
    elif args.command == "validate":
        _print_json(monitor_validation(file_path=args.file))
