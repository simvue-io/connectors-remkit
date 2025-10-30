"""
ReMKiT-1D Connector Example
========================
This is an example of the RemkitRun Connector class, displaying 3D metrics which vary across x through time.

The ReMKiT-1D simulation here simulates a single set of fluid plasma equations governs an advective wave of plasma with a Gaussian profile inside a reflective box. 
See Mijin et al Comp. Phys. Comms (2024) 300 109195 Sec.5.1.1.
 
To run this example with Docker:
    - Pull the base FDS image: docker run -it ghcr.io/simvue-io/remkit_example
    - Create a simvue.toml file, copying in your information from the Simvue server: nano simvue.toml
    - Run the example script: python examples/remkit_example_3D.py

To run this example on your own system with ReMKiT installed:
    - Ensure that you have ReMKiT-1D installed - see here for instructions: https://github.com/ukaea/ReMKiT1D
    - Clone this repository: git clone https://github.com/simvue-io/connectors-remkit.git
    - Move into Remkit directory: cd connectors-remkit
    - Create a simvue.toml file, copying in your information from the Simvue server: vi simvue.toml
    - Install Poetry: pip install poetry
    - Install required modules: poetry install
    - Check that the 'remkit_executable_path' set in run.launch() matches the installation path of ReMKiT on your system
    - Run the example script: poetry run python examples/remkit_example_3D.py
    
For a more in depth example, see: https://docs.simvue.io/examples/remkit/
"""

import pathlib
import uuid
from simvue_remkit.connector import RemkitRun

# Initialise the RemkitRun class as a context manager
with RemkitRun() as run:
    # Initialise the run, providing a name for the run, and optionally extra information such as a folder, description, tags etc
    run.init(
        name="remkit-kinetic-advection-%s" % str(uuid.uuid4()),
        description="An example of using the RemkitRun Connector to track a ReMKiT-1D simulation.",
        folder="/remkit/examples",
        tags=["remkit", "advection"],
    )
    
    # You can use any of the Simvue Run() methods to upload extra information before/after the simulation
    run.update_metadata({"example_name": "RMK_kin_adv_test"})

    # Then call the .launch() method to start your ReMKiT simulation, providing the path to the config file
    run.launch(
        remkit_executable_path = "/home/ReMKiT1D/build/src/executables/ReMKiT1D/ReMKiT1D",
        config_path = pathlib.Path(__file__).parent.joinpath("config_3D.json"),
        # You can optionally use the connector to define where to store results, whether to delete previous results, and which variables to track
        clean_results_dir = True
    )
    
    # Once the simulation is complete, you can upload any final items to the Simvue run before it closes
    num_output_files = sum(1 for f in pathlib.Path(__file__).parent.joinpath("3D_example_results").iterdir() if f.is_file())
    run.log_event(f"Simulation produced {num_output_files} results files.")
