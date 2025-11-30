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
Put the following json block into an MCP client (e.g. Claude Desktop).
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
On windows it might look something like this:
```json
{
  "mcpServers": {
    "SWMM": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "C:\\path\\to\\directory\\SWMM-MCP",
        "server.py"
      ]
    }
  }
}
```

If your client lets you use a system prompt, this has been working somewhat well.
```
You are an expert stormwater modeler specializing in EPA SWMM. You must use available tools to help users understand their 
models and interpret results. When the user asks a question, first identify which tools would be most helpful before proceeding.
Explain technical terms and provide context for results. 
Be friendly, helpful, and concise. End responses with 2-3 specific follow-up suggestions based on the analysis.
```

## Development
To test a tool without actually using an LLM, you can use the utility in `test.py`. Specify the following variables and run it either through an IDE, or with `uv run test.py`.
```python
# server.py : function to test
@mcp.tool()
def model_info(model_name):
    pass

# in test.py:  
tool_name = "model_info"
tool_parameters = {
    "model_name": "base_model"
}
```


To add a new python package, use the command:
```
uv add <package name>
```
This will take care of updating pyproject.toml and the lock file, keeping all of our environments on the same page.


## Troubleshooting

### Adding server to client failure
For mac users, you may run into an issue of the client being unable to find the path uv is installed. To resolve this issue, you can create a symlink to one of the paths the client already checks. 

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


