import json
import pytest

KNOWN_WALKS = {
    "BallWalk", "BilliardWalk", "AcceleratedBilliardWalk", "SparseBilliardWalk",
    "CDHRWalk", "RDHRWalk", "DikinWalk", "JohnWalk", "VaidyaWalk",
    "GaussianBallWalk", "GaussianCDHRWalk", "BilliardShakeAndBakeWalk",
    "ShakeAndBakeWalk", "BCDHRWalk", "BRDHRWalk", "CRHMCWalk",
}

REQUIRED_GLOBAL_KEYS = {
    "target_ESS", "time_limit_sec", "base_seed", "dimensions",
    "rotation_angle", "polytope_choice", "custom_A_file", "custom_b_file",
    "dynamic_batch_size", "write_to_file", "rounding", "auto_walk",
    "show_console_logs", "show_menu",
}

REQUIRED_WALK_KEYS = {"enabled", "samples", "walk_len_multiplier", "walk_len_base"}

VALID_POLYTOPES = {"Cube", "Custom"}


def validate_config(config: dict) -> list[str]:
    """Returns a list of human-readable problems; empty list = valid."""
    problems = []

    gs = config.get("global_settings")
    if gs is None:
        return ["missing 'global_settings' section"]

    missing_global = REQUIRED_GLOBAL_KEYS - gs.keys()
    if missing_global:
        problems.append(f"global_settings missing keys: {sorted(missing_global)}")

    if "dimensions" in gs:
        dims = gs["dimensions"]
        if not isinstance(dims, list) or not dims:
            problems.append("dimensions must be a non-empty list")
        else:
            bad = [d for d in dims if not isinstance(d, int) or d <= 0]
            if bad:
                problems.append(f"dimensions must be positive ints, got: {bad}")

    if "target_ESS" in gs and (not isinstance(gs["target_ESS"], (int, float)) or gs["target_ESS"] <= 0):
        problems.append("target_ESS must be a positive number")

    if "time_limit_sec" in gs and (not isinstance(gs["time_limit_sec"], (int, float)) or gs["time_limit_sec"] <= 0):
        problems.append("time_limit_sec must be a positive number")

    if gs.get("polytope_choice") not in VALID_POLYTOPES and "polytope_choice" in gs:

        problems.append(f"polytope_choice {gs.get('polytope_choice')!r} not in {VALID_POLYTOPES}")

    walks = config.get("walks")
    if walks is None:
        problems.append("missing 'walks' section")
        return problems

    unknown_walks = set(walks.keys()) - KNOWN_WALKS
    if unknown_walks:
        problems.append(f"unknown walk name(s): {sorted(unknown_walks)}")

    any_enabled = False
    for name, wcfg in walks.items():
        missing = REQUIRED_WALK_KEYS - wcfg.keys()
        if missing:
            problems.append(f"walk '{name}' missing keys: {sorted(missing)}")
            continue
        if wcfg["enabled"]:
            any_enabled = True
            if not isinstance(wcfg["samples"], int) or wcfg["samples"] <= 0:
                problems.append(f"walk '{name}' samples must be a positive int")
            if wcfg["walk_len_multiplier"] == 0 and wcfg["walk_len_base"] == 0:
                problems.append(f"walk '{name}' has walk_len_multiplier and walk_len_base both 0 "
                                 f"(walk length would be 0)")

    if not any_enabled:
        problems.append("no walk is enabled - benchmark would do nothing")

    return problems

def test_provided_config_is_valid(base_config):
    problems = validate_config(base_config)
    assert problems == []


def test_no_enabled_walk_is_flagged(base_config):
    for w in base_config["walks"].values():
        w["enabled"] = False
    problems = validate_config(base_config)
    assert any("no walk is enabled" in p for p in problems)


def test_unknown_walk_name_is_flagged(base_config):
    base_config["walks"]["TotallyMadeUpWalk"] = {
        "enabled": True, "samples": 10, "walk_len_multiplier": 1, "walk_len_base": 0
    }
    problems = validate_config(base_config)
    assert any("unknown walk" in p for p in problems)


@pytest.mark.parametrize("bad_dims", [[], [-5], [0], ["10"], None])
def test_invalid_dimensions_are_flagged(base_config, bad_dims):
    base_config["global_settings"]["dimensions"] = bad_dims
    problems = validate_config(base_config)
    assert any("dimensions" in p for p in problems)


@pytest.mark.parametrize("bad_samples", [0, -1, 3.5, "2000"])
def test_invalid_samples_flagged(base_config, bad_samples):
    base_config["walks"]["BilliardWalk"]["samples"] = bad_samples
    problems = validate_config(base_config)
    assert any("BilliardWalk" in p and "samples" in p for p in problems)


def test_zero_walk_length_flagged(base_config):
    base_config["walks"]["BilliardWalk"]["walk_len_multiplier"] = 0
    base_config["walks"]["BilliardWalk"]["walk_len_base"] = 0
    problems = validate_config(base_config)
    assert any("walk length would be 0" in p for p in problems)


def test_json_file_roundtrips(write_config, base_config):
    path = write_config(base_config)
    with open(path) as f:
        loaded = json.load(f)
    assert loaded == base_config
    assert validate_config(loaded) == []
