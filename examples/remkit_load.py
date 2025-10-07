"""
ReMKiT-1D Connector Example
========================
This is an example of the RemkitRun Connector class, loading results from an existing simulation into Simvue.

The ReMKiT-1D simulation here simulates.....

To run this example with Docker:
    - Pull the base FDS image: docker run -it ghcr.io/simvue-io/remkit_example
    - Create a simvue.toml file, copying in your information from the Simvue server: nano simvue.toml
    - Run the example script: python examples/remkit_load.py

To run this example on your own system with ReMKiT installed:
    - Ensure that you have ReMKiT-1D installed - see here for instructions: https://github.com/ukaea/ReMKiT1D
    - Clone this repository: git clone https://github.com/simvue-io/connectors-remkit.git
    - Move into Remkit directory: cd connectors-remkit
    - Create a simvue.toml file, copying in your information from the Simvue server: vi simvue.toml
    - Install Poetry: pip install poetry
    - Install required modules: poetry install
    - Check that the 'remkit_executable_path' set in run.launch() matches the installation path of ReMKiT on your system
    - Run the example script: poetry run python examples/remkit_load.py
    
For a more in depth example, see: https://docs.simvue.io/examples/remkit/
"""

import pathlib
import shutil
import uuid
from simvue_remkit.connector import RemkitRun

# Initialise the RemkitRun class as a context manager
with RemkitRun() as run:
    # Initialise the run, providing a name for the run, and optionally extra information such as a folder, description, tags etc
    run.init(
        name="remkit-advection-outflow-%s" % str(uuid.uuid4()),
        description="An example of using the RemkitRun Connector to load a ReMKiT-1D simulation.",
        folder="/remkit/examples",
        tags=["remkit", "advection"],
    )
    
    # You can use any of the Simvue Run() methods to upload extra information before/after the simulation
    run.update_metadata({"example_name": "RMK_advection_cm"})

    # Then call the .load() method to load your ReMKiT simulation, providing the path to results directory
    run.load(
        results_dir_path = pathlib.Path(__file__).parent.joinpath("RMK_advection_cm"),
        # If you have access to it, also provide the location of the ReMKiT-1D config file:
        config_path = pathlib.Path(__file__).parent.joinpath("RMK_advection_cm", "config.json"),
    )
    
    # Once the simulation is complete, you can upload any final items to the Simvue run before it closes
    num_output_files = sum(1 for f in pathlib.Path(__file__).parent.joinpath("RMK_advection_cm").iterdir() if f.is_file())
    run.log_event(f"Found {num_output_files} results files.")