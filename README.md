# Simvue Connectors - ReMKiT-1D

<br/>

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://github.com/simvue-io/.github/blob/5eb8cfd2edd3269259eccd508029f269d993282f/simvue-white.png" />
    <source media="(prefers-color-scheme: light)" srcset="https://github.com/simvue-io/.github/blob/5eb8cfd2edd3269259eccd508029f269d993282f/simvue-black.png" />
    <img alt="Simvue" src="https://github.com/simvue-io/.github/blob/5eb8cfd2edd3269259eccd508029f269d993282f/simvue-black.png" width="500">
  </picture>
</p>

<p align="center">
Allows simple connection between Simvue and ReMKiT-1D (Reactive Multifluid and Kinetic Transport in 1D), allowing for easy tracking and monitoring of tokamak scrape-off layer simulations in real time.
</p>

<div align="center">
<a href="https://github.com/simvue-io/client/blob/main/LICENSE" target="_blank"><img src="https://img.shields.io/github/license/simvue-io/client"/></a>
<img src="https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue">
</div>

<h3 align="center">
 <a href="https://simvue.io"><b>Website</b></a>
  •
  <a href="https://docs.simvue.io"><b>Documentation</b></a>
</h3>

## Implementation
A customised `RemkitRun` class has been created which automatically does the following:

* Uploads your ReMKiT-1D config file as an input artifact
* Uploads information from the config file as metadata
* Tracks the ReMKiT simulation itself, alerting the user via the web UI if the simulation crashes unexpectedly
* Tracks the outputs from the simulation as they are created, uploading them as 1D, 2D or 3D metrics
* Uploads all results as output artifacts

The `RemkitRun` class also inherits from the `Run` class of the Simvue Python API, allowing for further detailed control over how your simulation is tracked.


## Installation
To install and use this connector, first create a virtual environment:
```
python -m venv venv
```
Then activate it:
```
source venv/bin/activate
```
And then use pip to install this module:
```
pip install simvue-remkit
```

## Configuration
The server URL and token can be defined as environment variables:
```sh
export SIMVUE_URL=...
export SIMVUE_TOKEN=...
```
or a `simvue.toml` file can be created containing:
```toml
[server]
url = "..."
token = "..."
```
The exact contents of both of the above options can be obtained directly by clicking the **Create new run** button on the web UI. Note that the environment variables have preference over the config file.

## Usage example
```python
from simvue_remkit.connector import RemkitRun

...

if __name__ == "__main__":

    ...

    # Using a context manager means that the status will be set to completed automatically,
    # and also means that if the code exits with an exception this will be reported to Simvue
    with RemkitRun() as run:

        # Specify a run name, along with any other optional parameters:
        run.init(
          name = 'my-remkit-simulation',                                  # Run name
          metadata = {'simulation_type': 'kinetic_advection'},            # Metadata
          tags = ['remkit', 'advection'],                                 # Tags
          description = 'ReMKiT simulation of tokamak scrape off layer.', # Description
          folder = '/remkit/kinetic-advection/trial_1'                    # Folder path
        )

        # Set folder details if necessary
        run.set_folder_details(
          metadata = {'simulation_type': 'kinetic_advection'},             # Metadata
          tags = ['remkit'],                                               # Tags
          description = 'ReMKiT simulations of tokamak scrape off layers'  # Description
        )

        # Can use the base Simvue Run() methods to upload extra information, eg:
        import os
        run.save_file(os.path.abspath(__file__), "code")

        # Launch the ReMKiT simulation
        run.launch(
            remkit_executable_path='path/to/remkit/executable',  # Path to your ReMKiT executable
            config_path='path/to/my/config_file.json',           # Path to the config file for this simulation
            vars_to_track=['T', 'f'],                            # Optional, specify a set of variables to track
            results_dir_path='path/to/my/results_dir',           # Optional, set a results directory for this run
            clean_results_dir=True                               # Optional, whether to clear pre-existing results before running
            )

```
You can also use the connector to load in results from previous simulations:
```python
from simvue_remkit.connector import RemkitRun

...

if __name__ == "__main__":

    with RemkitRun() as run:

        # Specify a run name, along with any other optional parameters:
        run.init(
          name = 'my-remkit-simulation',                                  # Run name
          metadata = {'simulation_type': 'kinetic_advection'},            # Metadata
          tags = ['remkit', 'advection'],                                 # Tags
          description = 'ReMKiT simulation of tokamak scrape off layer.', # Description
          folder = '/remkit/kinetic-advection/trial_1'                    # Folder path
        )

        # Can use the base Simvue Run() methods to upload extra information, eg:
        run.save_file(os.path.abspath(__file__), "code")

        # Load from a directory of results from a previous ReMKiT simulation
        run.load(
            results_dir_path='path/to/my/results_dir',  # Path to a directory of results from a ReMKiT simulation
            config_path='path/to/my/config_file.json',  # Optional, path to the config file for this simulation
            vars_to_track=['T', 'f'],                   # Optional, specify a set of variables to track
            )

```
## License

Released under the terms of the [GPL-3.0](https://github.com/simvue-io/connectors-remkit/blob/main/LICENSE) license.

## Citation

To reference Simvue, please use the information outlined in this [citation file](https://github.com/simvue-io/python-api/blob/dev/CITATION.cff).
