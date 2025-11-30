import os
import shutil
from swmm_api import SwmmInput, SwmmOutput, SwmmReport
from pyswmm import Simulation


MODELS_DIRECTORY = os.path.join(os.getcwd(), "models")

# We want to keep the model stored globally between tool-calls to keep things as snappy as possible.
current_model = {
    "name": '',
    "inp": None,
    "out": None,
    "rpt": None
}


class ModelManager:
    def __init__(self):
        # Get a list of models
        self._fetch_models()

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
        shutil.copyfile(path, new_path)
        self._fetch_models()
        return new_name

    def get(self, model_name, file):
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
        path = os.path.join(MODELS_DIRECTORY, model_name + ".inp")
        inp_object.write_file(path)


    # In the future we should multi-thread this thing so it doesn't block up the mcp server.
    # The only reason I'm not doing it right now is to keep things lean and simple.
    def run_model(self, model_name):
        """Runs the model with the given name."""
        global current_model
        try:
            if model_name not in self.__models:
                # Try refreshing the model list.
                self._fetch_models()
                if model_name not in self.__models:
                    return "Cannot find model. Double check the spelling."
            if os.path.exists(os.path.join(MODELS_DIRECTORY, model_name + ".out")):
                # Already ran
                return "Model already ran."
            elif model_name != current_model["name"]:
                with Simulation(os.path.join(MODELS_DIRECTORY, model_name + ".inp")) as sim:
                    for step in sim:
                        pass
        except Exception as e:
            print("Error running model: ", str(e))
            return "Error running model."
        return "Sucessfully ran model."
