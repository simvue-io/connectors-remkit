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
import shutil
from RMK_support.grid import gridFromDict
from RMK_support.IO_support import loadFromHDF5
class RemkitRun(WrappedRun):
    
    def _parse_hfd5(
        self, input_file: str, **__
    ) -> tuple[dict[str, typing.Any], list[dict[str, typing.Any]]]:
        dataset = loadFromHDF5(grid=self.grid, varNames=self.vars_to_track, filepaths=[input_file]).dataset
        metrics = {"time": dataset["t"].item()}
        # Loop through each variable
        for var in list(dataset.data_vars):
            # Find which coords it is defined over
            # Only care about dimensions with size > 1
            var_coords = [coord for coord in dataset[var].coords if len(dataset[coord]) > 1]
            # We will treat h separately - this is the harmonic number and we want different plots for each
            if "h" in var_coords:
                var_coords.remove("h")
                harmonics = list(dataset["h"].values)
            else:
                harmonics = None
            # If all axes have size 1, plot as a 1D metric
            if len(var_coords) == 0:
                if not harmonics:
                    metrics[var] = dataset[var].item()
                else:
                    for harmonic in harmonics:
                        metrics[f"{var}_harmonic_{harmonic}"] = dataset[var].sel(h=harmonic).item() # will this indexing work   
            # Otherwise plot as a multi-dimensional metric
            else:
                if not harmonics:
                    if self._first_file:
                        self.assign_metric_to_grid(
                            metric_name=var,
                            axes_ticks=[dataset[coord].values for coord in var_coords],
                            axes_labels=var_coords
                        )
                    metrics[var] = dataset[var].values
                else:
                    for harmonic in harmonics:
                        if self._first_file:
                            self.assign_metric_to_grid(
                                metric_name=f"{var}_harmonic_{harmonic}",
                                axes_ticks=[dataset[coord].values for coord in var_coords],
                                axes_labels=var_coords
                        )
                        metrics[f"{var}_harmonic_{harmonic}"] = dataset[var].sel(h=harmonic).values
        self._first_file = False
        return {}, metrics    
    
    def _var_callback(self, data, meta):
        time = data.pop("time", None)
        self.log_metrics(data, time=time)
        
    def _pre_simulation(self):
        """Upload any preliminary metadata etc and start the simulation process."""
        super()._pre_simulation()
        
        self.save_file(self.config_path, category="input")
        
        with open(self.config_path, "r") as config_file:
            config_dict = json.load(config_file)
            
        self.grid = gridFromDict(config_dict)
        
        vars_available = config_dict["HDF5"].get("outputVars", [])
        if not vars_available:
            raise ValueError("No variables are set to be output in the confg file!")
        elif not self.vars_to_track:
            self.vars_to_track = vars_available
        elif (vars_unavailable := [var for var in self.vars_to_track if var not in vars_available]):
            raise ValueError(f"Variable(s) requested not found in config file: {vars_unavailable}")
        
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
        
        #TODO: This is a 5000+ line file. Should we only upload certain bits?
        # Possibly ignore grid points and initial vals of variables?
        self.update_metadata({"ReMKiT1D": config_dict})
            
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
        for file in self.out_path.iterdir():
            self.save_file(file, category="output")

        super()._post_simulation()

    @simvue.utilities.prettify_pydantic
    @pydantic.validate_call
    def launch(
        self,
        remkit_executable_path: pydantic.FilePath, # TODO: better solution for this?
        config_path: pydantic.FilePath,
        vars_to_track: list[str] | None = None,
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
        
        self.vars_to_track = vars_to_track
        self._first_file = True
        
        super().launch()