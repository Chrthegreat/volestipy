import os
import pandas as pd
import pytest

pytest.importorskip("volestipy", reason="compiled volestipy extension not available")
import volestipy

ALL_WALKS = [
    "BallWalk", "BilliardWalk", "AcceleratedBilliardWalk", "SparseBilliardWalk",
    "CDHRWalk", "RDHRWalk", "DikinWalk", "JohnWalk", "VaidyaWalk",
    "GaussianBallWalk", "GaussianCDHRWalk", "BilliardShakeAndBakeWalk",
    "ShakeAndBakeWalk", "BCDHRWalk", "BRDHRWalk", "CRHMCWalk",
]

pytestmark = pytest.mark.integration

def _single_walk_config(walk_name, dim=2, samples=200, extra=None):
    walk_cfg = {"enabled": True, "samples": samples, "walk_len_multiplier": 0, "walk_len_base": 1}
    if extra:
        walk_cfg.update(extra)
    return {
        "global_settings": {
            "target_ESS": 100,
            "time_limit_sec": 5.0,
            "base_seed": 1,
            "dimensions": [dim],
            "rotation_angle": 0,
            "polytope_choice": "Cube",
            "custom_A_file": "",
            "custom_b_file": "",
            "dynamic_batch_size": True,
            "write_to_file": True,
            "rounding": False,
            "auto_walk": False,
            "show_console_logs": False,
            "show_menu": False,
        },
        "walks": {walk_name: walk_cfg},
    }


def test_fast_config_end_to_end(tmp_cwd, write_config, fast_config):
    path = write_config(fast_config)

    volestipy.run_benchmark(["--config", path])

    assert os.path.exists("benchmark_results.csv")
    df = pd.read_csv("benchmark_results.csv")
    assert len(df) > 0


@pytest.mark.parametrize("walk_name", ALL_WALKS)
def test_each_walk_runs_without_crashing(tmp_cwd, write_config, walk_name):
    extra = {"a_i_param": 1.0} if "Gaussian" in walk_name else None
    config = _single_walk_config(walk_name, extra=extra)
    path = write_config(config)

    volestipy.run_benchmark(["--config", path])

    assert os.path.exists("benchmark_results.csv")


def test_time_limit_is_respected(tmp_cwd, write_config):
    import time
    config = _single_walk_config("BallWalk", dim=30, samples=10_000)
    config["global_settings"]["time_limit_sec"] = 2.0
    config["global_settings"]["target_ESS"] = 5000
    path = write_config(config)

    start = time.time()
    volestipy.run_benchmark(["--config", path])
    elapsed = time.time() - start

    assert elapsed < 15.0, f"time_limit_sec=2.0 was not respected, took {elapsed:.1f}s"
