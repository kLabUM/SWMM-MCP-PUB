import os
from swmm_api import SwmmInput, SwmmOutput, SwmmReport
from pyswmm import Simulation
from utils.logger import log_info

MODELS_DIRECTORY = os.path.join(os.getcwd(), "models")

# We want to keep the model stored globally between tool-calls to keep things as snappy as possible.
current_model = {
    "name": '',
    "inp": type[SwmmInput],
    "out": type[SwmmOutput],
    "rpt": type[SwmmReport]
}


class ModelManager:
    def __init__(self):
        self.MODELS_DIRECTORY = MODELS_DIRECTORY
        # Get a list of models
        self._fetch_models()
        self._editable_models = []

    def _fetch_models(self):
        """Refreshes the list of models."""
        # Get a list of file names
        file_list = os.listdir(MODELS_DIRECTORY)

        # Remove the file if it doesn't end in .inp
        file_list = list(filter(lambda x: x.endswith(".inp"), file_list))

        # Chop off the file extension of each file
        file_list = list(map(lambda x: x.split(".")[0], file_list))
        self.__models = file_list

    def models(self):
        """Returns a list of available models in the server."""
        self._fetch_models() # Make sure we return an up-to-date list
        return self.__models

    def duplicate_model(self, model_name, new_name):
        """
        Duplicates a model and returns the new model name.
        ALWAYS use this before testing scenarios.
        """
        path = os.path.join(MODELS_DIRECTORY, model_name + ".inp")
        new_path = os.path.join(MODELS_DIRECTORY, new_name + ".inp")
        os.system(f"cp {path} {new_path}")
        self._fetch_models()
        self._editable_models.append(new_name)
        return new_name

    def upload_model(self, model_name: str, content: str) -> str:
        """
        Uploads a new SWMM model to the server.
        Returns success message or error description.
        """
        if not model_name:
            return "Error: Model name cannot be empty."

        if not content:
            return "Error: Model content cannot be empty."

        # Sanitize model name to prevent directory traversal
        model_name = model_name.replace("/", "_").replace("\\", "_").replace("..", "_")

        self._fetch_models()

        # Check if model already exists
        if model_name in self.__models:
            return f"Error: Model '{model_name}' already exists. Please choose a different name."

        file_path = os.path.join(MODELS_DIRECTORY, model_name + ".inp")

        try:
            with open(file_path, 'w') as f:
                f.write(content)

            # Validate the file by trying to load it
            SwmmInput(file_path)

            self._fetch_models()
            #self._editable_models.append(model_name) # Gonna keep it non-editable
            log_info(f"Successfully uploaded model: {model_name}")
            return f"Successfully uploaded model '{model_name}'. The model is now available for use."
        except Exception as e:
            # If validation fails, remove the file
            if os.path.exists(file_path):
                os.remove(file_path)
            log_info(f"Failed to upload model {model_name}: {str(e)}")
            return f"Error: Failed to upload model. The file may not be a valid SWMM input file. Details: {str(e)}"

    def get(self, model_name, file) -> SwmmInput | SwmmOutput | SwmmReport | None:
        """Returns the requested file for the given model."""
        global current_model

        path = os.path.join(MODELS_DIRECTORY, model_name + "." + file)

        try:
            if model_name not in self.__models:
                # Try refreshing the model list.
                self._fetch_models()
                if model_name not in self.__models:
                    return None

            elif not os.path.exists(path):
                return None

            elif model_name != current_model["name"]:
                current_model["name"] = model_name

                # Since we're switching to a new model, we need to invalidate all the other stored objects.
                all_endings = ["inp", "out", "rpt"]
                all_endings.remove(file)
                for ending in all_endings:
                    current_model[ending] = None

            match file:
                case "inp":
                    current_model["inp"] = SwmmInput(path)
                case "out":
                    current_model["out"] = SwmmOutput(path)
                case "rpt":
                    current_model["rpt"] = SwmmReport(path)

        except Exception as e:
            print("Error getting model: ", str(e))
            return None

        return current_model[file]

    def update_inp(self, model_name, inp_object: SwmmInput):
        if model_name not in self._editable_models:
            raise ValueError(f"Model '{model_name}' is not editable. You may only edit models that you have created.")

        path = os.path.join(MODELS_DIRECTORY, model_name + ".inp")
        inp_object.write_file(path)

        # This action should invalidate the current model's simulation results
        try:
            os.remove(os.path.join(MODELS_DIRECTORY, model_name + ".rpt"))
            os.remove(os.path.join(MODELS_DIRECTORY, model_name + ".out"))
        except FileNotFoundError:
            pass

    async def run_model(self, model_name):
        """Runs the model with the given name."""
        global current_model

        try:
            if model_name not in self.__models:
                # Try refreshing the model list.
                self._fetch_models()
                if model_name not in self.__models:
                    return "Cannot find model. Double check the spelling."

            out_path = os.path.join(MODELS_DIRECTORY, model_name + ".out")

            if os.path.exists(out_path):
                # Already ran
                return "Model already ran."

            inp_path = os.path.join(MODELS_DIRECTORY, model_name + ".inp")
            log_info(f"Starting simulation with inp file: {inp_path}")
            with Simulation(inp_path) as sim:
                log_info("Simulation started, beginning iteration")
                for step in sim:
                    pass
            log_info("Simulation completed successfully")

        except Exception as e:
            print("Error running model: ", str(e))
            return "Error running model."
        return "Successfully ran model."
