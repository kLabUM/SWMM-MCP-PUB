# SWMM-MCP
MCP Toolbox for SWMM

## Setup
1. [Install uv](https://docs.astral.sh/uv/getting-started/installation/)
2. Clone this repository
3. Install dependencies with:
```
uv sync
```

## Usage
Put the following json block into an MCP client (e.g. Claude Desktop). Though, some clients may have a different interface for configuring MCP servers.
If you are currently in the root folder of this project in your IDE, you can find your full directory path by entering the command `pwd`.
```json
{
  "mcpServers": {
    "SWMM": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/<path/to/directory>/SWMM-MCP",
        "server.py"
      ]
    }
  }
}
```
On Windows it may look something like this:
```json
{
  "mcpServers": {
    "SWMM": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "C:\\Users\\Jacob\\Documents\\SWMM-MCP",
        "server.py"
      ]
    }
  }
}
```

Example system prompt if allowed by your client:
```
You are an expert SWMM (Storm Water Management Model) assistant. You have access to tools to inspect and analyze SWMM models. Use the available tools to answer questions accurately.
```

## Inventory
### Tools
| Tool | Description                                                                                                                                                 |
| --- |-------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `list_models` | Returns a list of available models in the server.                                                                                                           |
| `duplicate_model` | Duplicates a model and returns the new model name. Useful for testing scenarios.                                                                        |
| `get_model_info` | Returns general information about a model.                                           |
| `get_input_sections` | Returns a list of sections in the input file for a given model.                                                                                             |
| `get_input_info` | Returns the contents of a section of the input file for a given model. |
| `add_storage` | Replace a junction with a cylindrical storage node of specified volume.  |
| `change_conduit` | Changes the diameter of a circular conduit in the model.                                                                                                    |
| `run_model` | Runs a model.                                                                                                                                               |
| `get_report_sections` | Returns a list of sections in the report file for a given model.                                                                                            |
| `get_report_info` | Returns the contents of a section of the report file for a given model.                                                                                     |
| `get_output_variables` | Returns a list of variables in the output file for a given model.                                                                                           |
| `get_output_objects` | Returns a list of objects in the output file for a given model and object type.                                                                             |
| `change_storm` | Modify the model's storm event to an 24-hour SCS Type 2 design storm of a given depth.                                                                      |

### Apps
| App | Description                                                                                                                                                 |
| --- |-------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `prompt_model_upload` | Prompts the user with a UI where they can upload a SWMM model.                                                                                              |
| `plot_output_data` | Displays a full timeseries plot to the user.                                                                                |
| `plot_model_map` | Creates an interactive map of the SWMM model and displays it to the user.                          |
| `plot_rainfall` | Displays a timeseries plot of the model's rainfall to the user.                                 |

### Prompts
| Name | Description |
| --- | --- |
| `list_models` | Which models are available? |
| `describe_model` | Tell me about the model. |
| `get_pipes_and_junctions` | How many pipes and junctions does it have? |
| `largest_pipe` | What's the largest pipe in the network? |
| `show_network` | Show me my network |
| `run_model` | Run a model for me |
| `compare_flow_largest_pipe` | Compare flow through the largest pipe for a 2-inch vs 4-inch storm. |
| `nodes_flood_4_inch` | Which nodes flood under a 4-inch storm? |
| `detention_recommendations` | Suggest detention locations to reduce downstream flooding. |
| `add_storage_and_rerun` | Add a storage unit at a node and rerun. |
| `node_flow_timeseries` | Show node flow during the simulation. |
| `compare_base_to_modified` | Compare base and modified scenarios. |
| `outfall_hydrograph_comparison` | Plot base vs. modified outfall hydrographs. |


## Troubleshooting

### Adding server to client failure
For macOS users, you may run into an issue of the client being unable to find the path uv is installed. To resolve this issue, you can create a symlink to one of the paths the client already checks. 

To first find where uv is installed, in your terminal run:

```
which uv
```

which will return something like: 
`/Users/<user-name>/.local/bin/uv`


Then, to create a symlink, in your terminal run:

```
sudo ln -s ~/.local/bin/uv /usr/local/bin/uv
```
where `~/.local/bin/uv` is where uv is installed and `/usr/local/bin/uv` is part of the path your client checks. The error logs from the client should contain the paths it checks for uv. 


