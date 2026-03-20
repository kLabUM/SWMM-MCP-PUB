"""
Helpful logging stuff.
"""

import logging
from functools import wraps
from pprint import pformat
import asyncio

logger = logging.getLogger("SWMM_MCP")
logger.setLevel(logging.DEBUG)

file_handler = logging.FileHandler('server.log')
file_handler.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s : %(message)s', datefmt='%m/%d/%Y %H:%M:%S')
file_handler.setFormatter(formatter)

logger.addHandler(file_handler)

# Prevent propagation to the root logger
logger.propagate = False

# Can use this if you need to log something that isn't a tool call
def log_info(message):
    logger.info(message)

# Function decorator for MCP endpoints
# Usage:
# @mcp.tool()
# @tool_logger
# def my_tool(arg1: str):
def tool_logger(func):
    if asyncio.iscoroutinefunction(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            log_info(f"[Tool Called] {func.__name__} {kwargs}")
            response = await func(*args, **kwargs)
            log_info(f"[Tool Response]\n{pformat(response, width=100, compact=True)}\n")
            return response
        return async_wrapper
    else:
        @wraps(func)
        def wrapper(*args, **kwargs):
            log_info(f"[Tool Called] {func.__name__} {kwargs}")
            response = func(*args, **kwargs)
            log_info(f"[Tool Response]\n{pformat(response, width=100, compact=True)}\n")
            return response
        return wrapper