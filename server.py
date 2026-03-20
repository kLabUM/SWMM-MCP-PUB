import swmm_api.input_file.section_labels
from swmm_api.input_file.sections import Storage
from mcp import types
from fastmcp import FastMCP
from fastmcp.server.apps import AppConfig, ResourceCSP
from fastmcp.tools import ToolResult
from utils.ModelManager import ModelManager
from utils.NpEncoder import safe_json
from swmm_api.input_file import macros as inp_macros
import sys
import io
import pandas as pd
import plotly.graph_objects as go
from utils.logger import tool_logger, log_info
from utils.swmm_plotting import plot_network_map, plot_timeseries_generalized
from utils.design_storm import make_scs_storm
from prompts import register_prompts

mcp = FastMCP(
    name="SWMM-Interface",
    instructions="""
    This server provides tools for interfacing with SWMM models.
    """
)

register_prompts(mcp)

OUTPUT_NOT_FOUND_MESSAGE = "This resource does not exist. It is possible the simulation has not yet been run or it has not finished yet.\
 Please check the spelling and try again."

VISUALIZATION_VIEW_URI = "ui://swmm-interface/visualization_view.html"
UPLOAD_VIEW_URI = "ui://swmm-interface/upload_view.html"

mm = ModelManager()

@mcp.tool()
@tool_logger
def list_models() -> list[str]:
    """Returns a list of available models in the server."""
    return mm.models()

@mcp.tool()
@tool_logger
def duplicate_model(model_name: str, new_name: str) -> str:
    """Duplicates a model and returns the new model name. Use this for testing scenarios."""
    mm.duplicate_model(model_name, new_name)
    return new_name

@mcp.tool(app=AppConfig(resource_uri=UPLOAD_VIEW_URI))
@tool_logger
def prompt_model_upload() -> str:
    """Prompts the user with a UI where they can upload a SWMM model."""
    return "Success"

@mcp.tool(app=AppConfig(visibility=["app"]))
@tool_logger
def upload_model(model_name: str, content: str) -> str:
    """Uploads a new SWMM model to the server. The content should be the full .inp file content."""
    return mm.upload_model(model_name, content)

@mcp.tool()
@tool_logger
def get_model_info(model_name: str) -> dict | str:
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
#                             INPUT FILE STUFF
@mcp.tool()
@tool_logger
def get_input_sections(model_name: str):
    """Returns a list of sections in the input file for a given model. """
    model = mm.get(model_name, "inp")
    if model is None:
        return "This model does not exist. Please check the spelling and try again."
    return list(model.keys())

@mcp.tool()
@tool_logger
def get_input_info(model_name: str, section: str) -> dict | str:
    """
    Returns the contents of a section of the input file for a given model.
    Do NOT include brackets in the section name. Refer to the tool get_input_sections for a list of sections.

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


@mcp.tool()
@tool_logger
def add_storage(model_name: str, junction_name: str, storage_volume_cuft: float, initial_depth: float = 0, max_depth: float = None) -> str:
    """
    Replace a junction with a cylindrical storage node of specified volume. Unless specified, it will start empty. Returns success message or error description.
    """
    if model_name is None or junction_name is None or storage_volume_cuft is None:
        return "Missing required input parameters. Please provide model_name, junction_name, and storage_volume_cuft."
    if storage_volume_cuft <= 0:
        return "Storage volume must be greater than zero."

    model = mm.get(model_name, "inp")
    if model is None:
        return "This model does not exist. Please check the spelling and try again."

    junctions = getattr(model, "JUNCTIONS", None)
    if junctions is None or junction_name not in junctions:
        return f"Junction '{junction_name}' does not exist in model '{model_name}'."
    # Safe to go through with the conversion

    if getattr(model, "STORAGE", None) is None:
        model.STORAGE = Storage.create_section()

    junction_elevation = junctions[junction_name]["elevation"]
    junction_depth_max = junctions[junction_name]["depth_max"]

    if max_depth is not None:
        junction_depth_max = max_depth

    surface_area = storage_volume_cuft / junction_depth_max

    # Keep the same name to keep conduits connected.
    new_storage = Storage(name=junction_name, elevation=junction_elevation, depth_max=junction_depth_max,
                                  depth_init=initial_depth, kind=Storage.TYPES.FUNCTIONAL, data=[surface_area, 0, 0])
    model.STORAGE.add_obj(new_storage)

    del model["JUNCTIONS"][junction_name]

    try:
        mm.update_inp(model_name, model)
    except ValueError as er:
        return f"Error updating model: {er}"

    return f"Successfully added {new_storage}"

@mcp.tool()
@tool_logger
def change_conduit(model_name: str, conduit_name: str, new_diameter: float) -> str:
    """Changes the diameter of a circular conduit in the model."""
    if new_diameter < 0:
        return "Diameter must be at least zero."

    model = mm.get(model_name, "inp")
    if model is None:
        return "This model does not exist. Please check the spelling and try again."

    conduits = getattr(model, "XSECTIONS", None)
    if conduits is None or conduit_name not in conduits:
        return f"Junction '{conduit_name}' does not exist in model '{model_name}'."

    # Assert circular shape
    if model["XSECTIONS"][conduit_name].shape != "CIRCULAR":
        return f"Conduit '{conduit_name}' is not circular. Only circular conduits are supported."

    model["XSECTIONS"][conduit_name].height = new_diameter

    try:
        mm.update_inp(model_name, model)
    except ValueError as er:
        return f"Error updating model: {er}"

    return f"Successfully changed conduit {conduit_name} in model {model_name}"

# ===================================================================================
#                              RUN MODEL
@mcp.tool(task=True)
@tool_logger
async def run_model(model_name: str):
    """Runs a model."""
    stdout = sys.stdout
    stderr = sys.stderr

    sys.stdout = sys.stderr
    res = await mm.run_model(model_name)

    sys.stdout = stdout
    sys.stderr = stderr
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
def get_report_info(model_name: str, section: str) -> dict | str:
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
#                           VISUALIZATION RESOURCES

@mcp.resource(
    VISUALIZATION_VIEW_URI,
    app=AppConfig(csp=ResourceCSP(resource_domains=["https://cdn.plot.ly", "https://unpkg.com"])),
)
def visualization_view() -> str:
    """Interactive visualization viewer."""
    with open("apps/view.html", "r") as f:
        return f.read()

@mcp.resource(
    UPLOAD_VIEW_URI,
    app=AppConfig(csp=ResourceCSP(resource_domains=["https://unpkg.com"])),
)
def upload_view() -> str:
    """Interactive model upload interface."""
    with open("apps/upload.html", "r") as f:
        return f.read()

# ===================================================================================
#                           MODEL OUTPUT
@mcp.tool()
@tool_logger
def get_output_variables(model_name: str) -> dict | str:
    """Returns a list of variables in the output file for a given model. """
    model = mm.get(model_name, "out")
    if model is None:
        return OUTPUT_NOT_FOUND_MESSAGE
    return model.variables

@mcp.tool()
@tool_logger
def get_output_objects(model_name: str, object_type: str) -> list[str] | str:
    """
    Returns a list of objects in the output file for a given model and object type.
    object_type: the type of object to return. E.g. "node", "link", "subcatchment". Refer to the tool "model_output_variables" for a list of types.
    """
    model = mm.get(model_name, "out")
    if model is None:
        return "This model does not exist. Please check the spelling and try again."
    return model.labels[object_type]

@mcp.tool(app=AppConfig(resource_uri=VISUALIZATION_VIEW_URI))
@tool_logger
def plot_output_data(model_names: list[str], object_type: str, object_label: str, variable: str) -> ToolResult:
    """
    Displays a full timeseries plot to the user.
    Returns a summary of the data.
    model_names: List of model names to plot.
    object_type: the type of object to return. E.g. "node", "link", "subcatchment". Refer to the tool "get_output_variables" for a list of types.
    object_label: the label of the object in the output file. E.g. "J1", "S1"
    variable: the variable to return. E.g. "flow". Refer to the tool "get_output_variables" for a list of variables.
    """

    if len(model_names) == 0:
        return ToolResult(content=[types.TextContent(type="text", text="Please enter at least one model name.")], isError=True)

    summary_dict = {}
    fig = go.Figure()

    for model_name in model_names:
        model = mm.get(model_name, "out")
        if model is None:
            return ToolResult(content=[types.TextContent(type="text", text=f"Model {model_name} does not exist. Please check the spelling and try again.")], isError=True)
        try:
            data = model.get_part(object_type, object_label, variable)
            if data.empty:
                return ToolResult(content=[types.TextContent(type="text", text="This object does not exist.")], isError=True)

            fig = plot_timeseries_generalized(fig, data, trace_name=model_name)

            # Return simple statistics about the series
            summary = data.describe()

            summary_dict[model_name] = safe_json(summary.to_frame().to_json(orient="index"))
        except Exception as e:
            return ToolResult(content=[types.TextContent(type="text", text=f"There was an error getting the data: {e}")], isError=True)

    summary_text = "\n".join([f"{model}: {summary}" for model, summary in summary_dict.items()])

    return ToolResult(
        content=[
            types.TextContent(
                type="text",
                text=fig.to_json(),
                _meta={
                    "chartData": True
                }
            ),
            types.TextContent(
                type="text",
                text=f"Output data plotted successfully.\n\nSummary statistics:\n{summary_text}"
            )
        ]
    )

@mcp.tool(app=AppConfig(resource_uri=VISUALIZATION_VIEW_URI))
def plot_model_map(model_name: str) -> ToolResult:
    """Creates an interactive map of the SWMM model using Plotly and displays it to the user.
    Returns whether the operation was successful."""

    model = mm.get(model_name, "inp")
    if model is None:
        return ToolResult(content=[types.TextContent(type="text", text="This model does not exist. Please check the spelling and try again.")], isError=True)

    try:
        fig = plot_network_map(model)

        return ToolResult(
            content=[
                types.TextContent(
                    type="text",
                    text=fig.to_json(),
                    _meta={
                        "chartData": True
                    }
                ),
                types.TextContent(
                    type="text",
                    text=f"Model map for '{model_name}' displayed successfully."
                )
            ]
        )
    except Exception as e:
        return ToolResult(content=[types.TextContent(type="text", text=f"Error creating map: {str(e)}")], isError=True)

# ===================================================================================
#                           MODEL RAINFALL

@mcp.tool(app=AppConfig(resource_uri=VISUALIZATION_VIEW_URI))
@tool_logger
def plot_rainfall(model_name: str) -> ToolResult:
    """
    Displays a timeseries plot of the model's rainfall to the user.
    Returns the name of the timeseries or an error message.
    """
    model = mm.get(model_name, "inp")
    if model is None:
        return ToolResult(content=[types.TextContent(type="text", text="This model does not exist. Please check the spelling and try again.")], isError=True)

    gage = getattr(model, "RAINGAGES", None)
    if gage is None:
        return ToolResult(content=[types.TextContent(type="text", text="Error: Raingage not found.")], isError=True)

    if not gage[list(gage.keys())[0]]["source"] == "TIMESERIES":
        return ToolResult(content=[types.TextContent(type="text", text=f"Error: Only timeseries raingages are supported at this time, not source {gage[list(gage.keys())[0]]["source"]}.")], isError=True)

    timeseries_name = gage[list(gage.keys())[0]]["timeseries"]
    timeseries = getattr(model, "TIMESERIES", None)
    if timeseries is None:
        return ToolResult(content=[types.TextContent(type="text", text="Error: Timeseries not found.")], isError=True)

    timeseries = timeseries[timeseries_name]
    timeseries_name = timeseries['name']

    timeseries = timeseries['data']
    hours, rainfall = zip(*timeseries)
    rainfall_series = pd.Series(rainfall, index=hours, name=timeseries_name)

    fig = go.Figure()
    fig = plot_timeseries_generalized(fig, rainfall_series, x_label="Hours", y_label="Rainfall (inches)")

    return ToolResult(
        content=[
            types.TextContent(
                type="text",
                text=fig.to_json(),
                _meta={
                    "chartData": True
                }
            ),
            types.TextContent(
                type="text",
                text=f"Rainfall timeseries '{timeseries_name}' plotted successfully."
            )
        ]
    )


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

    """
    Editing the model:
    1) Clear the timeseries section
    2) Add the new timeseries
    3) Edit every rain gage to
        1) Use this new timeseries
        2) Have a form of "VOLUME"
        3) Use an interval of "0:15" (15 minutes)
    """

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

    try:
        mm.update_inp(model_name, model)
    except ValueError as er:
        return f"Error updating model: {er}"

    return new_storm_name


if __name__ == "__main__":
    try:
        mcp.run()
    except Exception as e:
        log_info(f"Error starting server: {e}")
