""" Connector.
===============

This module provides functionality for using Simvue to track and monitor a simulation.
"""
import pydantic

import simvue
from simvue_connector.connector import WrappedRun
import pydantic
import pathlib
import json
import multiparser.parsing.file as mp_file_parser
import typing
import h5py
import numpy
import shutil
from loguru import logger
class RemkitRun(WrappedRun):
    
    def _parse_hfd5(
        self, input_file: str, **__
    ) -> tuple[dict[str, typing.Any], list[dict[str, typing.Any]]]:
        with h5py.File(input_file, 'r') as file:
            return {}, {key: numpy.array(file[key][:]) for key in file.keys()}
        
    def _grid_callback(self, data, meta):
        if data["x"].shape[0] > 1:
            self._x_grid = data["x"]
        elif data["v"].shape[0] > 1:
            self._v_grid = data["v"]
        else:
            raise ValueError("Could not find position or velocity grid data")
    
    def _var_callback(self, data, meta):
        time = data.pop("time", None)
        x_axis = self._x_grid if self._x_grid is not None else self._v_grid
        # TODO: should we do a sleep() here if both x and v grid are not available? Maybe grid coords file read slightly after initial var results?
        label = "position" if self._x_grid is not None else "velocity"
        # Either provide dict of 2D arrays, or dict of 1D var arrays and a single array of x
        metrics = {key: numpy.stack((x_axis, value), axis=-1) for key, value in data.items()}
        # TODO: log metrics as 2D
        # For now just store in big dict
        self._all_metrics[self._step] = {"time": time, "data": metrics}
        
        self._step += 1
        
    def _pre_simulation(self):
        """Upload any preliminary metadata etc and start the simulation process."""
        super()._pre_simulation()
        
        self.save_file(self.config_path, category="input")
        
        with open(self.config_path, "r") as config_file:
            config_dict = json.load(config_file)
            
        #TODO: This is a 5000+ line file. Should we only upload certain bits?
        # Possibly ignore grid points and initial vals of variables?
        self.update_metadata({"ReMKiT1D": config_dict})
        
        if self.out_path and config_dict.get("HDF5"):
            config_dict["HDF5"]["filepath"] = str(self.out_path)+"/"
            with open(self.config_path, "w") as config_file:
                json.dump(config_dict, config_file)
        elif not self.out_path and (out_path := config_dict.get("HDF5", {}).get("filepath")):
            self.out_path = pathlib.Path(out_path).absolute()
        else:
            raise ValueError("Output directory path not provided, and not found in config file!")
        if self.clean_results_dir:
            shutil.rmtree(self.out_path)
            self.out_path.mkdir()

        if len(list(self.out_path.iterdir())) > 0:
            raise FileExistsError("Results directory is not empty! Please clear this before launching a simulation.")
            
        if (num_procs_h := config_dict.get("MPI", {}).get("numProcsH")) and (num_procs_x := config_dict.get("MPI", {}).get("numProcsX")):
            num_procs = num_procs_h * num_procs_x
        else:
            num_procs = 1
            
        self.add_process(
            "ReMKiT_Process",
            "mpirun",
            "-n",
            str(num_procs),
            str(self.remkit_executable_path),
            cwd=self.config_path.parent,
            completion_trigger=self._trigger
        )

        
    def _during_simulation(self):
        """Describe which files should be monitored during the simulation by Multiparser."""
        self.file_monitor.track(
            path_glob_exprs=str(pathlib.Path(self.out_path).joinpath("ReMKiT1DGridOutput.h5")),
            parser_func=mp_file_parser.file_parser(self._parse_hfd5),
            callback=self._grid_callback,
            static=True
        )
        self.file_monitor.track(
            path_glob_exprs=str(pathlib.Path(self.out_path).joinpath("ReMKiT1DVarOutput"))+"*.h5",
            parser_func=mp_file_parser.file_parser(self._parse_hfd5),
            callback=self._var_callback,
            static=True
        )
        
    def _post_simulation(self):
        """Do any required post-processing, upload output files etc after the simulation has finished."""
        # for file in self.out_path.iterdir():
        #     self.save_file(file, category="output")

        super()._post_simulation()

    @simvue.utilities.prettify_pydantic
    @pydantic.validate_call
    def launch(
        self,
        remkit_executable_path: pydantic.FilePath, # TODO: better solution for this?
        config_path: pydantic.FilePath,
        results_dir_path: str | None = None, # Will overwrite in config dict
        clean_results_dir: bool = True
        
    ):
        """Command to launch the simulation and track it with Simvue.
        """
        if not pathlib.Path(remkit_executable_path).exists():
            raise ValueError("Could not find ReMKiT executable")
        if not pathlib.Path(config_path).exists():
            raise ValueError("Could not find config file")
        
        self.out_path = None
        self.remkit_executable_path = remkit_executable_path
        self.config_path = config_path
        self.clean_results_dir = clean_results_dir
        
        if results_dir_path:
            pathlib.Path(results_dir_path).mkdir(parents=True, exist_ok=True)
            self.out_path =  pathlib.Path(results_dir_path).absolute()
        
        self._x_grid = None
        self._v_grid = None
        self._step = 0
        
        # TODO: Wont need this when metric logging available
        self._all_metrics = {}
        
        super().launch()
