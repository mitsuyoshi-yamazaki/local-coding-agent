"""既定の道具の組。起動のときに、これをループに渡す。"""

from local_coding_agent.tools import edit_file, list_directory, read_file, write_file
from local_coding_agent.tools.tool import Tool

DEFAULT_TOOLS: tuple[Tool, ...] = (
    read_file.TOOL,
    list_directory.TOOL,
    write_file.TOOL,
    edit_file.TOOL,
)
