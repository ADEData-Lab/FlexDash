"""
Unit tests for Capacity Market verification ETL.
"""

import sys
from pathlib import Path

import pandas as pd

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.analysis.cm_benchmark import build_cm_benchmark, load_verification_config


def test_load_verification_config_paths_exist_as_paths():
    project_root = Path(__file__).parent.parent
    cfg, raw = load_verification_config(project_root)
    assert cfg.dy
    assert cfg.unit
    assert isinstance(cfg.t1_appendix_a, Path)
    assert isinstance(cfg.t4_appendix_a, Path)
    assert "benchmark" in raw


def test_build_cm_benchmark_with_inputs_has_expected_schema():
    project_root = Path(__file__).parent.parent
    df = build_cm_benchmark(project_root)
    assert isinstance(df, pd.DataFrame)
    assert set(df.columns) == {"asset_class", "cm_benchmark_kw"}
    assert not df.empty
    assert (df["cm_benchmark_kw"] >= 0).all()
