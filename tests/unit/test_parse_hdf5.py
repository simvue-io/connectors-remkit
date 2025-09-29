import pytest
import pathlib
import json
from simvue_remkit.connector import RemkitRun
from RMK_support.grid import gridFromDict
from unittest.mock import patch
import numpy

def mock_create_grids(self, dataset):
    self._grids_created = True

@patch.object(RemkitRun, "_create_grids", mock_create_grids)
def test_parse_hdf5_2D():
    with open(pathlib.Path(__file__).parents[1].joinpath("example_data", "RMK_advection_test", "config.json"), "r") as config_file:
        config = json.load(config_file)
    with RemkitRun() as run:
        run.grid = gridFromDict(config)
        run.dual_vars = ["n_dual", "G_dual"]
        run.vars_to_track = ["time", "n", "n_dual", "G", "G_dual"]
        run._var_coords = None
        meta, metrics = run._parse_hdf5(str(pathlib.Path(__file__).parents[1].joinpath("example_data", "RMK_advection_test", "ReMKiT1DVarOutput_0.h5")))
        
    # Check 1D metric time is a float, not a list of one value
    assert isinstance(metrics.get("time"), float)
    
    # Check 2D metrics have been created as arrays
    for var in ("n", "n_dual", "G", "G_dual"):
        assert isinstance(metrics.get(var), numpy.ndarray)
        assert metrics.get(var).shape == (512,)
        
    # Check step information correctly added
    assert metrics["step"] == 0

@patch.object(RemkitRun, "_create_grids", mock_create_grids)
def test_parse_hdf5_3D_harmonics():
    with open(pathlib.Path(__file__).parents[1].joinpath("example_data", "RMK_kin_adv_test", "config.json"), "r") as config_file:
        config = json.load(config_file)
    with RemkitRun() as run:
        run.grid = gridFromDict(config)
        run.vars_to_track = ["time", "f"]
        run.dual_vars = []
        run._var_coords = None
        meta, metrics = run._parse_hdf5(str(pathlib.Path(__file__).parents[1].joinpath("example_data", "RMK_kin_adv_test", "ReMKiT1DVarOutput_0.h5")))
        
    # Check 1D metric time is a float, not a list of one value
    assert isinstance(metrics.get("time"), float)
    
    # Check 3D metrics have been created as arrays
    # Check they have been transposed
    # Check one created for each harmonic
    for var in ("f_harmonic_0", "f_harmonic_1"):
        assert isinstance(metrics.get(var), numpy.ndarray)
        assert metrics.get(var).shape == (80, 128)
    
    # Check step information correctly added
    assert metrics["step"] == 0
    