import pytest
import pathlib
import json
from simvue_remkit.connector import RemkitRun
@pytest.mark.parametrize(
    ("variable", "dual"),
    [
        ("n", False),
        ("G_dual", True),
        ("G", False),
        ("n_dual", True)
    ],
    ids=["implicit_non_dual", "implicit_dual", "derived_non_dual", "derived_dual"]
)
def test_on_dual_grid(variable, dual):
    with open(pathlib.Path(__file__).parent.joinpath("example_data", "RMK_advection_test", "config.json"), "r") as config_file:
        config = json.load(config_file)
    with RemkitRun() as run:
        is_dual = run._is_on_dual_grid(config, variable)
        
    assert is_dual == dual