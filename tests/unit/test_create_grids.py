import pytest
from simvue_remkit.connector import RemkitRun
import xarray
import numpy

from unittest.mock import patch, MagicMock

CALL_COUNT = 0

def mock_assign_metrics_to_grid(self, metric_name, axes_ticks, axes_labels, **kwargs):
    global CALL_COUNT
    CALL_COUNT += 1
    self.metric_name = metric_name
    self.axes_ticks = axes_ticks
    self.axes_labels = axes_labels
    return

@patch.object(RemkitRun, "assign_metric_to_grid", mock_assign_metrics_to_grid)
@pytest.mark.parametrize(
    "var_coords",
    [
        {
            "axes": [],
            "harmonics": None
        },
        {
            "axes": ["x"],
            "harmonics": None
        },
        {
            "axes": ["x_dual"],
            "harmonics": None
        },
        {
            "axes": ["x"],
            "harmonics": [0, 1]
        },
        {
            "axes": ["x_dual"],
            "harmonics": [2, 3]
        },
        {
            "axes": ["x", "v"],
            "harmonics": None
        },
        {
            "axes": ["x_dual", "v"],
            "harmonics": None
        },
        {
            "axes": ["x", "v"],
            "harmonics": [0, 1]
        },
    ],
    ids=["no_axes", "x", "x_dual", "x-harmonics", "x_dual-harmonics", "x-v", "x_dual-v", "x-v-harmonics"]
)
def test_create_grid(var_coords):
    global CALL_COUNT
    CALL_COUNT = 0
    coords={
        "x": numpy.linspace(0, 10, 10),
        "x_dual": numpy.linspace(10, 20, 10),
        "v": numpy.linspace(20, 30, 10)
    }
    dataset = xarray.Dataset(
        {
            "test_var": (["x"], numpy.random.rand(10)),
        },
        coords=coords
    )
    with RemkitRun() as run:
        run._var_coords = {
            "test_var": var_coords
        }
        run._create_grids(dataset)
        
    assert run._grids_created
    
    if not var_coords["axes"]:
        # If no variable axes, metric is 1D, so dont assign to grid
        assert CALL_COUNT == 0
    elif not var_coords["harmonics"]:
        assert CALL_COUNT == 1
        assert run.metric_name == "test_var"
        assert run.axes_ticks == [coords[axis] for axis in var_coords["axes"]]
        assert run.axes_labels == var_coords["axes"]
    else:
        assert CALL_COUNT == 2
        assert run.metric_name == f"test_var_harmonic_{var_coords['harmonics'][-1]}"
        assert run.axes_ticks == [coords[axis] for axis in var_coords["axes"]]
        assert run.axes_labels == var_coords["axes"]