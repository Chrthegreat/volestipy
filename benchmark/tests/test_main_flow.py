import importlib
import sys
import types
import pandas as pd
import pytest

MODULE_NAME = "run_benchmark" 


@pytest.fixture
def script_module(monkeypatch, fake_volestipy_module):
    fake_volestipy_module("success")  

    plot_calls = []
    fake_plot_module = types.ModuleType("plot")

    def fake_plot_results(csv_file, start_row=0):
        plot_calls.append({"csv_file": csv_file, "start_row": start_row})

    fake_plot_module.plot_results = fake_plot_results
    monkeypatch.setitem(sys.modules, "plot", fake_plot_module)

    sys.modules.pop(MODULE_NAME, None)
    mod = importlib.import_module(MODULE_NAME)
    mod._plot_calls = plot_calls  # stash for assertions
    return mod


def _get_fake_volestipy():
    return sys.modules["volestipy"]


def test_success_path_calls_plot_once_with_start_row_zero(tmp_cwd, write_config, base_config, script_module):
    write_config(base_config)
    script_module.main()

    assert len(script_module._plot_calls) == 1
    assert script_module._plot_calls[0]["start_row"] == 0
    fake = _get_fake_volestipy()
    assert len(fake.calls) == 1


def test_config_path_passed_correctly(tmp_cwd, write_config, base_config, script_module):
    """The wrapper builds argv as ["--config", <abs path>] - verify that's
    actually what reaches run_benchmark, since a relative/wrong path here
    would fail deep inside C++ with a much less clear error."""
    write_config(base_config)
    script_module.main()

    fake = _get_fake_volestipy()
    args = fake.calls[0]
    assert "--config" in args
    config_arg = args[args.index("--config") + 1]
    assert config_arg.endswith("walk_config.json")
    import os
    assert os.path.isabs(config_arg)


def test_keyboard_interrupt_still_plots_and_does_not_propagate(tmp_cwd, write_config, base_config,
                                                                 fake_volestipy_module, script_module):
    fake_volestipy_module("keyboard_interrupt")
    write_config(base_config)

    script_module.main()

    assert len(script_module._plot_calls) == 1


def test_crash_still_plots_partial_data(tmp_cwd, write_config, base_config,
                                         fake_volestipy_module, script_module):
    fake_volestipy_module("crash")
    write_config(base_config)

    script_module.main() 

    assert len(script_module._plot_calls) == 1
    df = pd.read_csv("benchmark_results.csv")
    assert len(df) == 1  


def test_start_row_offset_on_rerun(tmp_cwd, write_config, base_config,
                                    fake_volestipy_module, script_module):
    """Run the benchmark twice against an existing CSV - the second call's
    plot should be told to start at the row count from the first run,
    not re-plot everything from scratch."""
    fake_volestipy_module("success")
    write_config(base_config)

    script_module.main()
    first_len = len(pd.read_csv("benchmark_results.csv"))

    script_module.main()
    assert script_module._plot_calls[-1]["start_row"] == first_len


def test_missing_config_file_is_handled_gracefully(tmp_cwd, base_config, script_module):
    """Don't write any config file - main() should hit the except branch
    (or fail clearly) rather than hanging or crashing pytest itself."""
    fake = _get_fake_volestipy()
    fake.behavior = "crash"

    script_module.main()
    assert len(script_module._plot_calls) == 1
