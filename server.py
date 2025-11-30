import webbrowser
import swmm_api.input_file.section_labels
from fastmcp import FastMCP
from utils.model_manager import ModelManager
from utils.numpy_encoder import safe_json
from swmm_api.input_file import macros as inp_macros
import sys
import io
import pandas as pd
import plotly.graph_objects as go
from utils.logger import tool_logger, log_info
import time
from utils.visualization_server import VisualizationServer
from utils.swmm_plotting import plot_network_map, plot_timeseries_generalized
from utils.design_storm import make_scs_storm

mcp = FastMCP(
    name="SWMM-Interface",
    instructions="""
    This server provides tools for interfacing with SWMM models.
    """
)

OUTPUT_NOT_FOUND_MESSAGE = "This resource does not exist. It is possible the simulation has not yet been run or it has not finished yet.\
 Please check the spelling and try again."

mm = ModelManager()
visual_server = None

@mcp.tool()
@tool_logger
def list_models() -> list[str]:
    """Returns a list of available models in the server."""
    return mm.models()

@mcp.tool()
@tool_logger
def duplicate_model(model_name: str, new_name) -> str:
    """Duplicates a model and returns the new model name. Use this for testing scenarios."""
    mm.duplicate_model(model_name, new_name)
    return new_name

@mcp.tool()
@tool_logger
def model_info(model_name) -> dict | str:
    """Returns general information about a model. Be sure to enter the model name exactly as it appears in the list."""
    model = mm.get(model_name, "inp")
    if model is None:
        return "This model does not exist. Please check the spelling and try again."

    # We have to do this because swmm_api only lets you print a summary to stdout, when we want to return it.
    old_stdout = sys.stdout
    redirected_output = io.StringIO()
    sys.stdout = redirected_output

    try:
        inp_macros.summarize.print_summary(model)
        summary_string = redirected_output.getvalue()
    finally:
        # Restore stdout
        sys.stdout = old_stdout

    return summary_string.replace("\n", ", ")


# ==============================================================================
#                             INPUT FILE
@mcp.tool()
@tool_logger
def get_model_sections(model_name: str):
    """Returns a list of sections in the input file for a given model. """
    model = mm.get(model_name, "inp")
    if model is None:
        return "This model does not exist. Please check the spelling and try again."
    return list(model.keys())

@mcp.tool()
@tool_logger
def input_file_info(model_name: str, section: str) -> dict | str:
    """
    Returns the contents of a section of the input file for a given model.
    Do NOT include brackets in the section name. Refer to the tool get_model_sections for a list of sections.

    """
    model = mm.get(model_name, "inp")
    if model is None:
        return "This model does not exist. Please check the spelling and try again."

    section_resp = getattr(model, section, None)
    if section_resp is None:
        return "This section does not exist."

    # replace NaN
    section_resp = section_resp.get_dataframe()
    section_resp = section_resp.fillna("NaN")
    try:
        return safe_json(section_resp.to_dict(orient="index"))
    except Exception as e:
        return safe_json(section_resp)

# ===================================================================================
#                              RUN MODEL
@mcp.tool()
@tool_logger
def run_model(model_name: str):
    """Runs a model."""
    res = mm.run_model(model_name)
    return res


# ===================================================================================
#                           MODEL REPORT
@mcp.tool()
@tool_logger
def get_report_sections(model_name: str) -> list[str] | str:
    """Returns a list of sections in the report file for a given model. """
    model = mm.get(model_name, "rpt")
    if model is None:
        return OUTPUT_NOT_FOUND_MESSAGE

    sections = model.available_parts
    sections = [s.lower().replace(" ", "_") for s in sections]
    sections.remove("version+title")

    return sections

@mcp.tool()
@tool_logger
def get_report_file_info(model_name: str, section: str) -> dict | str:
    """Returns the contents of a section of the report file for a given model. """
    model = mm.get(model_name, "rpt")
    if model is None:
        return OUTPUT_NOT_FOUND_MESSAGE

    section_resp = getattr(model, section, None)
    if section_resp is None:
        return "This section does not exist."

    try:
        return safe_json(section_resp.to_dict(orient="index"))
    except Exception as e:
        return safe_json(section_resp)


# ===================================================================================
#                           MODEL OUTPUT
@mcp.tool()
@tool_logger
def get_model_output_variables(model_name: str) -> dict | str:
    """Returns a list of variables in the output file for a given model. """
    model = mm.get(model_name, "out")
    if model is None:
        return OUTPUT_NOT_FOUND_MESSAGE
    return model.variables

@mcp.tool()
@tool_logger
def get_model_output_objects(model_name: str, object_type: str) -> list[str] | str:
    """
    Returns a list of objects in the output file for a given model and object type.
    object_type: the type of object to return. E.g. "node", "link", "subcatchment". Refer to the tool "model_output_variables" for a list of types.
    """
    model = mm.get(model_name, "out")
    if model is None:
        return "This model does not exist. Please check the spelling and try again."
    return model.labels[object_type]

@mcp.tool()
@tool_logger
def plot_model_output_data(model_names: list[str], object_type: str, object_label: str, variable: str) -> dict | str:
    """
    Displays a full timeseries plot to the user.
    Returns a summary of the data.
    model_names: List of model names to plot.
    object_type: the type of object to return. E.g. "node", "link", "subcatchment". Refer to the tool "model_output_variables" for a list of types.
    object_label: the label of the object in the output file. E.g. "J1", "S1"
    variable: the variable to return. E.g. "flow". Refer to the tool "model_output_variables" for a list of variables.
    """

    if len(model_names) == 0:
        return "Please enter at least one model name."

    summary_dict = {}
    fig = go.Figure()

    for model_name in model_names:
        model = mm.get(model_name, "out")
        if model is None:
            return f"Model {model_name} does not exist. Please check the spelling and try again."
        try:
            data = model.get_part(object_type, object_label, variable)
            if data.empty:
                return "This object does not exist."

            fig = plot_timeseries_generalized(fig, data, trace_name=model_name)

            # Return simple statistics about the series
            summary = data.describe()

            summary_dict[model_name] = safe_json(summary.to_frame().to_json(orient="index"))
        except Exception as e:
            return f"There was an error getting the data: {e}"

    visual_server.update_visualization(fig)
    return summary_dict


@mcp.tool()
def plot_model_map(model_name: str) -> str:
    """Creates an interactive map of the SWMM model using Plotly and displays it to the user.
    Returns whether the operation was successful."""

    model = mm.get(model_name, "inp")
    if model is None:
        return "This model does not exist. Please check the spelling and try again."

    try:
        fig = plot_network_map(model)
        visual_server.update_visualization(fig)

        return "Map displayed to the user successfully."
    except Exception as e:
        return f"Error creating map: {str(e)}"


# ===================================================================================
#                           MODEL RAINFALL
@mcp.tool()
@tool_logger
def plot_rainfall(model_name: str) -> str:
    """
    Displays a timeseries plot of the model's rainfall to the user.
    Returns the name of the timeseries or an error message.
    """
    model = mm.get(model_name, "inp")
    if model is None:
        return "This model does not exist. Please check the spelling and try again."

    gage = getattr(model, "RAINGAGES", None)
    if gage is None:
        return "Error: Raingage not found."

    if not gage[list(gage.keys())[0]]["source"] == "TIMESERIES":
        return f"Error: Only timeseries raingages are supported at this time, not source {gage[list(gage.keys())[0]]["source"]}."

    timeseries_name = gage[list(gage.keys())[0]]["timeseries"]
    timeseries = getattr(model, "TIMESERIES", None)
    if timeseries is None:
        return "Error: Timeseries not found."

    timeseries = timeseries[timeseries_name]
    timeseries_name = timeseries['name']

    timeseries = timeseries['data']
    hours, rainfall = zip(*timeseries)
    rainfall_series = pd.Series(rainfall, index=hours, name=timeseries_name)

    fig = go.Figure()
    fig = plot_timeseries_generalized(fig, rainfall_series, x_label="Hours", y_label="Rainfall (inches)")
    visual_server.update_visualization(fig)

    return timeseries_name


@mcp.tool()
@tool_logger
def change_storm(model_name: str, depth: float) -> str:
    """
    Modify the model's storm event to an 24-hour SCS Type 2 design storm of a given depth.
    depth: Total rainfall depth in inches
    :return: Name of the new storm or error message
    """
    # Get the model
    model = mm.get(model_name, "inp")
    if model is None:
        return "This model does not exist. Please check the spelling and try again."

    gage = getattr(model, "RAINGAGES", None)
    if gage is None:
        return "Error generating new storm: Raingage not found."

    # We're sticking with 24 hour storms for now
    # Room to extend this feature to different durations later on
    # Only does intervals of 15 minutes for now
    timeseries = make_scs_storm(depth)
    new_storm_name = f"SCS_24H_TYPE_II_{depth}IN"

    # make tuple of time, rainfall
    timeseries_tuples = []
    for _, row in timeseries.iterrows():
        timeseries_tuples.append((float(row["time_hr"]), float(row["incremental_in"])))

    # new timeseries data object
    ts_data = swmm_api.input_file.sections.TimeseriesData(new_storm_name, timeseries_tuples)

    section = model["TIMESERIES"].create_new_empty()
    model.delete_section("TIMESERIES")
    model.add_new_section(section)
    model["TIMESERIES"][new_storm_name] = ts_data

    gages = getattr(model, "RAINGAGES", None)
    if gages is not None:
        for gage in gages:
            gages[gage]["source"] = "TIMESERIES"
            gages[gage]["timeseries"] = new_storm_name
            gages[gage]["form"] = "VOLUME"
            gages[gage]["interval"] = "0:15"
            gages[gage]["units"] = "IN"

    mm.update_inp(model_name, model)
    return new_storm_name


if __name__ == "__main__":
    # Clear the log file.
    with open("server.log", "w") as f:
        f.write("")

    stdout = sys.stdout
    stderr = sys.stderr

    visual_server = VisualizationServer()
    visual_server.start()
    time.sleep(2) # Wait a moment for the server to start
    webbrowser.open(f'http://localhost:{visual_server.port}')

    sys.stdout = stdout
    sys.stderr = stderr

    try:
        mcp.run()
    except Exception as e:
        log_info(f"Error starting server: {e}")