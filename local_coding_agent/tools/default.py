"""既定の道具の組。起動のときに、これをループに渡す。"""

from local_coding_agent.tools import list_directory, read_file
from local_coding_agent.tools.tool import Tool

DEFAULT_TOOLS: tuple[Tool, ...] = (read_file.TOOL, list_directory.TOOL)
