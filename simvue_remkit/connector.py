""" Connector.
===============

This module provides functionality for using Simvue to track and monitor a simulation.
"""
import pydantic
import time
import simvue
from simvue_connector.connector import WrappedRun
import pathlib
import json
import multiparser.parsing.file as mp_file_parser
import typing
import shutil
import h5py
import xarray
from RMK_support.grid import gridFromDict, Grid
from RMK_support.IO_support import loadFromHDF5
class RemkitRun(WrappedRun):
    
    def _get_var_axes(self, dataset: xarray.Dataset):
        """Get the axes and harmonics which each variable is defined over.

        Parameters
        ----------
        dataset : xarray.Dataset
            The dataset loaded from a ReMKiT VarOutput file
        """
        _var_coords = {}
        for var in list(dataset.data_vars):
            # Find which coords it is defined over
            # Only care about dimensions with size > 1
            var_axes = [axis for axis in dataset[var].coords if len(dataset[axis]) > 1]
            # We will treat h separately - this is the harmonic number and we want different plots for each
            if "h" in var_axes:
                var_axes.remove("h")
                harmonics = list(dataset["h"].values)
            else:
                harmonics = None
            _var_coords[var] = {
                "axes": var_axes,
                "harmonics": harmonics
            }
        self._var_coords = _var_coords
    
    def _create_grids(self, dataset: xarray.Dataset):
        """Create the Simvue grids requires for plotting multi-dimensional data based on axes of each ReMKiT variable.

        Parameters
        ----------
        dataset : xarray.Dataset
            The dataset loaded from a ReMKiT VarOutput file
        """
        for var, coords in self._var_coords.items():
            var_axes = coords.get("axes")
            if len(var_axes) > 0:
                if harmonics := coords.get("harmonics"):
                    for harmonic in harmonics:
                        self.assign_metric_to_grid(
                            metric_name=f"{var}_harmonic_{harmonic}",
                            axes_ticks=[dataset[axis].values for axis in var_axes],
                            axes_labels=var_axes
                        )
                else:
                    self.assign_metric_to_grid(
                        metric_name=var,
                        axes_ticks=[dataset[axis].values for axis in var_axes],
                        axes_labels=var_axes
                    )
        self._grids_created = True
    
    def _parse_hfd5(
        self, input_file: str, **__
    ) -> tuple[dict[str, typing.Any], list[dict[str, typing.Any]]]:
        """Parse a single VarOutput HDF5 file and extract the metrics to be uploaded to Simvue.

        Parameters
        ----------
        input_file : str
            The path to the HDF5 file

        Returns
        -------
        tuple[dict[str, typing.Any], list[dict[str, typing.Any]]]
            The metadata (blank) and metrics data extracted from the file
        """
        dataset = loadFromHDF5(grid=self.grid, varNames=self.vars_to_track, filepaths=[input_file]).dataset
        metrics = {"time": dataset["t"].item(), "step": int(input_file.split("_")[-1].split(".")[0])}
        
        if not self._var_coords:
            self._get_var_axes(dataset)
        if metrics["step"] == 0:
            self._create_grids(dataset)
            
        # Loop through each variable
        for var, coords in self._var_coords.items():
            # If all axes have size 1, plot as a 1D metric
            if len(coords.get("axes")) == 0:
                if harmonics := coords.get("harmonics"):
                    for harmonic in harmonics:
                        metrics[f"{var}_harmonic_{harmonic}"] = dataset[var].sel(h=harmonic).item() # TODO will this indexing work 
                    metrics[var] = dataset[var].item()
                else:
                    metrics[var] = dataset[var].item()
            # Otherwise plot as a multi-dimensional metric
            else:
                if harmonics := coords.get("harmonics"):
                    for harmonic in harmonics:
                        metrics[f"{var}_harmonic_{harmonic}"] = dataset[var].sel(h=harmonic).values
                else:
                    metrics[var] = dataset[var].values

        return {}, metrics    
    
    def _var_callback(self, data: dict[str, typing.Any], meta: dict[str, typing.Any]):
        """Upload the metrics to Simvue

        Parameters
        ----------
        data : dict[str, typing.Any]
            The metrics to upload
        meta : dict[str, typing.Any]
            The metadata for these metrics
        """
        metric_time = data.pop("time", None)
        metric_step = data.pop("step", None)
        while not self._grids_created:
            time.sleep(0.1)
            
        self.log_metrics(data, time=metric_time, step=metric_step)
        
    def _pre_simulation(self):
        """Method to run required setup tasks before simulation begins.
        
            - Read the config file, load the Grid to use in ReMKiT Python module
            - Update the results directory path in the config file if passed into launch
            - Check variables requested by the user are available in the config file
            - Upload config file as input artifact and metadata
            - Clean results directory if requested
            - Launch the simulation with num processors as requested in config file
        """
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
        if self.clean_results_dir and self.out_path.exists():
                shutil.rmtree(self.out_path)
        
        self.out_path.mkdir(parents=True, exist_ok=True)

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
            f"-with_config_path={str(self.config_path.absolute())}",
            completion_trigger=self._trigger
        )

        
    def _during_simulation(self):
        """Monitor the VarOutput files as they are created and extract metrics from them."""
        self.file_monitor.track(
            path_glob_exprs=str(pathlib.Path(self.out_path).joinpath("ReMKiT1DVarOutput"))+"*.h5",
            parser_func=mp_file_parser.file_parser(self._parse_hfd5),
            callback=self._var_callback,
            static=True
        )
        
    def _post_simulation(self):
        """Save all output files as output artifacts."""
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
        results_dir_path: str | None = None,
        clean_results_dir: bool = False
        
    ):
        """Launch a ReMKiT-1D simulation and track it with Simvue.

        Parameters
        ----------
        remkit_executable_path : pydantic.FilePath
            The path to the ReMKiT executable used to run the simulation
        config_path: pydantic.FilePath
            Path to the config file to use for this simulation
        vars_to_track : list[str] | None, optional
            The variables from your simulation to track using Simvue, by default None (will track all available variables)
        results_dir_path : str | None, optional
            The directory to store your results in (this will update the path in your config file)
            by default None, which uses the results directory path stored in your config file
        clean_results_dir : bool, optional
            Whether to delete all existing files in the results directory before starting the simulation, by default False

        Raises
        ------
        FileNotFoundError
            Raised if ReMKiT executable could not be found
        FileNotFoundError
            Raised if config file could not be found
        """
        if not pathlib.Path(remkit_executable_path).exists():
            raise FileNotFoundError("Could not find ReMKiT executable")
        if not pathlib.Path(config_path).exists():
            raise FileNotFoundError("Could not find config file")
        
        self.out_path = None
        self.remkit_executable_path = remkit_executable_path
        self.config_path = config_path
        self.clean_results_dir = clean_results_dir
        
        if results_dir_path:
            pathlib.Path(results_dir_path).mkdir(parents=True, exist_ok=True)
            self.out_path =  pathlib.Path(results_dir_path).absolute()
        
        self.vars_to_track = vars_to_track
        self._grids_created = False
        self._var_coords = None

        
        super().launch()
        
    def load(
        self,
        results_dir_path: pydantic.DirectoryPath,
        config_path: pydantic.FilePath | None = None,
        vars_to_track: list[str] | None = None,
    ):
        """Load results from a pre-existing set of ReMKiT results into Simvue.

        Parameters
        ----------
        results_dir_path : pydantic.DirectoryPath
            The path to the directory where results are stored
        config_path : pydantic.FilePath | None, optional
            The configuration file which was used by this simulation (if available), by default None
        vars_to_track : list[str] | None, optional
            The variables from your simulation to track using Simvue, by default None (will track all available variables)

        Raises
        ------
        FileNotFoundError
            Raised if results directory could not be found
        FileNotFoundError
            Raised if config file path is provided, and no file could be found
        FileNotFoundError
            Raised if no config file was provided, and no GridOutput file is present in the results directory to determine a grid from
        ValueError
            Raised if variables requested by user are not available in the results files

        """
        
        if not pathlib.Path(results_dir_path).exists():
            raise FileNotFoundError("Could not find results directory!")
        if config_path and not pathlib.Path(config_path).exists():
            raise FileNotFoundError("Could not find config file")
        
        self._grids_created = False
        self._var_coords = None
        self.vars_to_track = vars_to_track
        self.out_path =  pathlib.Path(results_dir_path).absolute()
        
        super()._pre_simulation()
        
        # If config file is provided, get the grid from that
        if config_path:
            self.save_file(config_path, category="input")
            with open(config_path, "r") as config_file:
                config_dict = json.load(config_file)
                
            self.grid = gridFromDict(config_dict)
            self.update_metadata(config_dict)
            
        # Otherwise, use the GridOutput file
        else:
            grid_file = pathlib.Path(results_dir_path).joinpath("ReMKiT1DGridOutput.h5")
            if not grid_file.exists():
                raise FileNotFoundError("Cannot determine grid - no config file provided and no GridOutput file found in results dir.")
            with h5py.File(grid_file, 'r') as grid_output:
                self.grid = Grid(
                    xGrid=grid_output.get("x")[()],
                    vGrid=grid_output.get("v")[()],
                    lMax=int(grid_output.get("l")[-1]),
                    mMax=int(grid_output.get("m")[-1]),
                )
                
        # Now glob through all files in the results dir
        results_files = list(pathlib.Path(results_dir_path).glob("ReMKiT1DVarOutput_*.h5"))
        results_files.sort()
        
        # Use the first file to get the variables available
        with h5py.File(results_files[0], 'r') as result_file:
            vars_available = list(result_file.keys())
            if not self.vars_to_track:
                self.vars_to_track = vars_available
            elif (vars_unavailable := [var for var in self.vars_to_track if var not in vars_available]):
                raise ValueError(f"Variable(s) requested not found in config file: {vars_unavailable}")
        
        for file in results_files:
            _, metrics = self._parse_hfd5(str(file))
            self._var_callback(metrics, {})
            
        self._post_simulation()
            
        
                
                       
