import pytest
import pathlib
import json
from simvue_remkit.connector import RemkitRun
from RMK_support.grid import gridFromDict
from unittest.mock import patch
import numpy
import tempfile
import simvue

@pytest.fixture
def setup_config_file():
    with tempfile.TemporaryDirectory() as tempdir:
        config = {
            "HDF5": {
                "outputVars": ["var_1", "var_2"],
                "filepath": f"{tempdir}/outputs"
            },
            "MPI": {
                "numProcsH": 2,
                "numProcsX": 2
            }
        }
        config_path = pathlib.Path(tempdir).joinpath("config.json")
        with open(config_path, "w") as config_file:
            json.dump(config, config_file)
        yield config_path, config
        

def mock_add_process(self, *args, **kwargs):
    self.process_command = " ".join(args)    

def mock_grid_from_dict(dict):
    return {}
    
@pytest.mark.parametrize(
    "vars_to_track", [
        None,
        ["var_1"],
        ["var_1", "invalid_var"]
    ],
    ids=["all_vars", "selected_var", "invalid_var"]
)    
@patch.object(RemkitRun, "add_process", mock_add_process)
@patch("simvue_remkit.connector.gridFromDict", new=mock_grid_from_dict)
def test_pre_simulation_vars(folder_setup, setup_config_file, vars_to_track):
    config_path, config = setup_config_file
    with RemkitRun() as run:
        run.config_path = config_path
        run.vars_to_track = vars_to_track
        run.out_path = None
        run.clean_results_dir = False
        run.remkit_executable_path = "remkit"
        run.init("test_pre_simulation", folder=folder_setup)
        
        if vars_to_track and "invalid_var" in vars_to_track:
            with pytest.raises(ValueError):
                run._pre_simulation()
            return
        else:
            run._pre_simulation()
        
        if vars_to_track:
            assert run.vars_to_track == ["var_1"]
        else:
            assert run.vars_to_track == ["var_1", "var_2"]
        
        assert run.process_command == f"ReMKiT_Process mpirun -n 4 remkit -with_config_path={config_path}"       
        
        client = simvue.Client()
        run = client.get_run(run.id)
        assert run.artifacts[0]["name"] == "config.json"
        assert run.metadata.get("ReMKiT1D") == config
        

    