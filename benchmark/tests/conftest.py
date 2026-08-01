"""
Shared pytest fixtures for the benchmark test suite.

Key idea: `run_benchmark` in the C++ module has no return value that's
useful to assert on directly (it just writes a CSV as a side effect and
may raise). So most unit tests fake `volestipy.run_benchmark` with a
Python stand-in that mimics its observable behavior (writes rows to the
CSV, or raises), which lets us test main()'s control flow (success /
KeyboardInterrupt / Exception -> always calls plot_results) without
needing the compiled extension or a real, slow sampling run at all.

The one real end-to-end test (test_integration.py) does call the actual
volestipy.run_benchmark, but with a deliberately tiny/fast config.
"""
import json
import os
import sys
import shutil
import pytest
import pandas as pd

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


@pytest.fixture
def tmp_cwd(tmp_path, monkeypatch):
    """Run the test inside an isolated temp directory (own cwd),
    since main() writes 'benchmark_results.csv' relative to cwd."""
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture
def base_config():
    """A full config matching your schema, as a Python dict, so tests
    can mutate/parametrize individual fields instead of hand-editing JSON."""
    return {
        "global_settings": {
            "target_ESS": 3000,
            "time_limit_sec": 30.0,
            "base_seed": 42,
            "dimensions": [10, 20, 30, 40, 50, 60],
            "rotation_angle": 53,
            "polytope_choice": "Cube",
            "custom_A_file": "Cube_50_A.csv",
            "custom_b_file": "Cube_50_b.csv",
            "dynamic_batch_size": True,
            "write_to_file": True,
            "rounding": False,
            "auto_walk": False,
            "show_console_logs": False,
            "show_menu": False,
        },
        "walks": {
            "BallWalk": {"enabled": False, "samples": 20000, "walk_len_multiplier": 2, "walk_len_base": 0},
            "BilliardWalk": {"enabled": True, "samples": 2000, "walk_len_multiplier": 0, "walk_len_base": 1},
            "AcceleratedBilliardWalk": {"enabled": True, "samples": 2000, "walk_len_multiplier": 0, "walk_len_base": 1},
            "SparseBilliardWalk": {"enabled": False, "samples": 1000, "walk_len_multiplier": 0, "walk_len_base": 1},
            "CDHRWalk": {"enabled": True, "samples": 1000, "walk_len_multiplier": 2, "walk_len_base": 0},
            "RDHRWalk": {"enabled": False, "samples": 1000, "walk_len_multiplier": 2, "walk_len_base": 0},
            "DikinWalk": {"enabled": False, "samples": 1000, "walk_len_multiplier": 2, "walk_len_base": 0},
            "JohnWalk": {"enabled": False, "samples": 1000, "walk_len_multiplier": 2, "walk_len_base": 0},
            "VaidyaWalk": {"enabled": False, "samples": 1000, "walk_len_multiplier": 2, "walk_len_base": 0},
            "GaussianBallWalk": {"enabled": False, "samples": 1000, "walk_len_multiplier": 2, "walk_len_base": 0, "a_i_param": 1.0},
            "GaussianCDHRWalk": {"enabled": False, "samples": 1000, "walk_len_multiplier": 2, "walk_len_base": 0, "a_i_param": 1.0},
            "BilliardShakeAndBakeWalk": {"enabled": False, "samples": 1000, "walk_len_multiplier": 2, "walk_len_base": 0},
            "ShakeAndBakeWalk": {"enabled": False, "samples": 1000, "walk_len_multiplier": 2, "walk_len_base": 0},
            "BCDHRWalk": {"enabled": False, "samples": 1000, "walk_len_multiplier": 2, "walk_len_base": 0},
            "BRDHRWalk": {"enabled": False, "samples": 1000, "walk_len_multiplier": 2, "walk_len_base": 0},
            "CRHMCWalk": {"enabled": False, "samples": 1000, "walk_len_multiplier": 0, "walk_len_base": 1},
        },
    }


@pytest.fixture
def fast_config():
    """A minimal config meant to actually finish in ~1-2s against the
    real C++ extension: one tiny dimension, one cheap walk, few samples,
    a hard time limit as a safety net."""
    return {
        "global_settings": {
            "target_ESS": 100,
            "time_limit_sec": 5.0,
            "base_seed": 1,
            "dimensions": [2],
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
        "walks": {
            "BilliardWalk": {"enabled": True, "samples": 200, "walk_len_multiplier": 0, "walk_len_base": 1},
        },
    }


@pytest.fixture
def write_config(tmp_cwd):
    """Helper: dump a config dict to walk_config.json in the tmp cwd,
    matching the path resolution main() uses (next to the script)."""
    def _write(config_dict, name="walk_config.json"):
        path = tmp_cwd / name
        path.write_text(json.dumps(config_dict, indent=2))
        return str(path)
    return _write


class FakeVolestipy:
    """Drop-in stand-in for the `volestipy` C++ extension module.

    Configure `.behavior` to control what run_benchmark() does:
      - "success": writes a couple of fake result rows to the CSV
      - "keyboard_interrupt": raises KeyboardInterrupt after writing partial rows
      - "crash": raises a RuntimeError after writing partial rows
      - "noop": does nothing (simulates e.g. all walks disabled)
    """
    def __init__(self, behavior="success", csv_file="benchmark_results.csv"):
        self.behavior = behavior
        self.csv_file = csv_file
        self.calls = []

    def run_benchmark(self, args):
        self.calls.append(list(args))

        def append_rows(rows):
            df = pd.DataFrame(rows)
            header = not os.path.exists(self.csv_file)
            df.to_csv(self.csv_file, mode="a", header=header, index=False)

        if self.behavior == "noop":
            return
        if self.behavior == "success":
            append_rows([{"walk": "BilliardWalk", "dim": 2, "ess": 150, "time_sec": 0.4}])
            return
        if self.behavior == "keyboard_interrupt":
            append_rows([{"walk": "BilliardWalk", "dim": 2, "ess": 40, "time_sec": 0.1}])
            raise KeyboardInterrupt()
        if self.behavior == "crash":
            append_rows([{"walk": "BilliardWalk", "dim": 2, "ess": 10, "time_sec": 0.05}])
            raise RuntimeError("simulated C++ crash (e.g. segfault-adjacent LP failure)")
        raise ValueError(f"unknown behavior {self.behavior}")


@pytest.fixture
def fake_volestipy_module(monkeypatch):
    """Install a FakeVolestipy() into sys.modules['volestipy'] so that
    `import volestipy` inside your benchmark script picks it up, and
    return the instance so tests can configure .behavior and inspect .calls."""
    def _install(behavior="success"):
        fake_module = FakeVolestipy(behavior=behavior)
        monkeypatch.setitem(sys.modules, "volestipy", fake_module)
        return fake_module
    return _install
