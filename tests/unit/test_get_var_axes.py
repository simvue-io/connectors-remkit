from simvue_remkit.connector import RemkitRun
import pathlib
import json

from RMK_support.IO_support import loadFromHDF5
from RMK_support.grid import gridFromDict


def test_get_var_axes_2d():
    with open(pathlib.Path(__file__).parents[1].joinpath("example_data", "RMK_advection_test", "config.json"), "r") as config_file:
        config = json.load(config_file)
    var_list = ["time", "n", "n_dual", "G", "G_dual"]
    grid = gridFromDict(config)
    data = loadFromHDF5(grid, var_list, [str(pathlib.Path(__file__).parents[1].joinpath("example_data", "RMK_advection_test","ReMKiT1DVarOutput_0.h5"))])
    with RemkitRun() as run:
        run.dual_vars = ["n_dual", "G_dual"]
        run._get_var_axes(data.dataset)
    
    # Check n_dual and G_dual have axes as 'x_dual'
    assert run._var_coords["n_dual"]["axes"] == ["x_dual"]
    assert run._var_coords["G_dual"]["axes"] == ["x_dual"]
    
    # Check time has no axes (1D metric)
    assert run._var_coords["time"]["axes"] == []
    
    # Check others have axes as 'x'
    assert run._var_coords["n"]["axes"] == ["x"]
    assert run._var_coords["G"]["axes"] == ["x"]

    # Check all have no harmonics
    for var in var_list:
        assert run._var_coords[var]["harmonics"] is None

def test_get_var_axes_3d():
    with open(pathlib.Path(__file__).parents[1].joinpath("example_data", "RMK_kin_adv_test", "config.json"), "r") as config_file:
        config = json.load(config_file)
    var_list = ["time", "f"]
    grid = gridFromDict(config)
    data = loadFromHDF5(grid, var_list, [str(pathlib.Path(__file__).parents[1].joinpath("example_data", "RMK_kin_adv_test","ReMKiT1DVarOutput_0.h5"))])
    with RemkitRun() as run:
        run.dual_vars = []
        run._get_var_axes(data.dataset)
    
    # Check f has both axes as 'x', 'v'
    assert run._var_coords["f"]["axes"] == ["x", "v"]
    
    # Check time has no axes (1D metric)
    assert run._var_coords["time"]["axes"] == []
    
    # Check f has harmonics, 0 and 1
    assert run._var_coords["f"]["harmonics"] == [0,1]