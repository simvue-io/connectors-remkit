import pytest
from simvue_remkit.connector import RemkitRun
import uuid
import pathlib
import time
import simvue
from simvue.sender import sender
import json
import requests
import numpy
import tempfile
import shutil

@pytest.mark.parametrize("offline", (True, False), ids=("offline", "online"))
@pytest.mark.parametrize("set_config_path", (True, False), ids=("config", "no-config"))
@pytest.mark.parametrize(
    ("results_dir", "vars_to_track", "all_vars", "slice_dims"),
    [
        ("RMK_advection_test", None, ["n", "n_dual", "G", "G_dual", "T", "W", "otherW"], (512,)),
        ("RMK_kin_adv_test", None, ["f_harmonic_0", "f_harmonic_1"], (128, 80)),
        ("RMK_advection_test", ["n", "n_dual", "G", "G_dual"], ["n", "n_dual", "G", "G_dual", "T", "W", "otherW"], (512,)),
        ("RMK_kin_adv_test", ["f"], ["f_harmonic_0", "f_harmonic_1"], (128, 80))
    ],
    ids=["advection-all_vars", "kin_adv-all_vars", "advection-tracked_vars", "kin_adv-tracked_vars"]
)
@pytest.mark.parametrize("launch", (True, False), ids=("launch", "load"))
def test_remkit_connector(folder_setup, offline, offline_cache_setup, launch, set_config_path, results_dir, vars_to_track, all_vars, slice_dims):
    with RemkitRun(mode="offline" if offline else "online") as run:
        run.init("test_remkit_connector-%s" % str(uuid.uuid4()), folder=folder_setup)
        if launch:
            if not pathlib.Path("/home/ReMKiT1D/build/src/executables/ReMKiT1D/ReMKiT1D").exists():
                raise pytest.skip("ReMKiT executable could not be found at expected location!")
            tempdir = tempfile.TemporaryDirectory()
            # Make temporary copy, overwrite results dir in config with temporary dir path
            config_path = pathlib.Path(tempdir.name).joinpath("config.json")
            results_path = f"{tempdir.name}/new_path/" if set_config_path else f"{tempdir.name}/old_path/"
            shutil.copy(pathlib.Path(__file__).parents[1].joinpath("example_data", results_dir, "config.json"), config_path)
            with open(config_path, "r") as config_file:
                config = json.load(config_file)
            config["HDF5"]["filepath"] = f"{tempdir.name}/old_path/"
            with open(config_path, "w") as config_file:
                json.dump(config, config_file)
            run.launch(
                remkit_executable_path = "/home/ReMKiT1D/build/src/executables/ReMKiT1D/ReMKiT1D",
                config_path = config_path,
                vars_to_track = vars_to_track,
                results_dir_path = f"{tempdir.name}/new_path/" if set_config_path else None,
            ) 

        else:
            config_path = pathlib.Path(__file__).parents[1].joinpath("example_data", results_dir, "config.json")
            results_path = pathlib.Path(__file__).parents[1].joinpath("example_data", results_dir)
            run.load(
                results_dir_path = results_path,
                config_path = config_path if set_config_path else None,
                vars_to_track = vars_to_track
            )
    time.sleep(1) 
    run_id = run.id
    
    if offline:
        _id_mapping = sender()
        run_id = _id_mapping.get(run_id)
        time.sleep(1)
    
    client = simvue.Client()
    retrieved_run = client.get_run(run_id)
    
    # Check config dict uploaded as artfact and metadata, if present
    with open(config_path, "r") as config_file:
        config_dict = json.load(config_file)
        
    if launch or set_config_path:
        assert [artifact["name"] for artifact in retrieved_run.artifacts if artifact["category"] == "input"][0] == "config.json"
        # Won't check the whole dict since Remkit sometimes overwrites and adds blank keys
        assert retrieved_run.metadata.get("ReMKiT1D")["HDF5"] == config_dict["HDF5"]
        
    # Check all results uploaded
    results_files = [path.name for path in pathlib.Path(results_path).iterdir()]
    artifact_names = [artifact["name"] for artifact in retrieved_run.artifacts if artifact["category"] == "output"]
    assert all(name in artifact_names for name in results_files)
        
    # Check 2D / 3D metrics uploaded
    # TODO: Improve this when client methods available
    for metric in all_vars:
        response = requests.get(
            url=f"{run._user_config.server.url}/runs/{retrieved_run.id}/metrics/{metric}/values?step=10",
            headers={
                "Authorization": f"Bearer {run._user_config.server.token.get_secret_value()}",
                "Accept-Encoding": "gzip",
            },
        )
        if vars_to_track and metric.split("_harmonic")[0] not in vars_to_track:
            assert response.status_code == 404
        else:
            assert response.status_code == 200   
            assert numpy.array(response.json().get("array")).T.shape == slice_dims
            
    if launch:
        tempdir.cleanup()