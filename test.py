"""
Framework for testing endpoints during development.
"""

from fastmcp import Client
import asyncio
from server import mcp
import pprint

# ========= CONFIG ===========

tool_name = "list_models"
tool_parameters = {
}

# ============================

async def main():
    global tool_name, tool_parameters

    async with Client(mcp) as client:
        result = await client.call_tool(tool_name, tool_parameters)

        if result:
            if result.data:
                pprint.pprint(result.data)
            elif result.content:
                pprint.pprint(result.content)
            else:
                pprint.pprint(result)
            return result

        print("Nothing returned from tool.")
        return None

if __name__ == "__main__":
    asyncio.run(main())