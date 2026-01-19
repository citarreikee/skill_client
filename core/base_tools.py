"""
Base Tools for Skill Execution
Provides file operations, bash execution, and directory management
"""

import os
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List


class BaseToolExecutor:
    """Executor for base tools that skills need to function"""

    def __init__(self, working_directory: Optional[str] = None):
        """Initialize tool executor

        Args:
            working_directory: Base directory for file operations (defaults to cwd)
        """
        self.working_directory = Path(working_directory or os.getcwd())

        # Tool registry: name -> handler function
        self.tools = {
            "read_file": self._read_file,
            "write_file": self._write_file,
            "list_files": self._list_files,
            "execute_bash": self._execute_bash,
            "create_directory": self._create_directory,
        }

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Get OpenAI-compatible tool definitions

        Returns:
            List of tool definition dicts
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": "Read contents of a file. Supports text and binary files.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Path to the file to read (relative or absolute)"
                            }
                        },
                        "required": ["path"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "write_file",
                    "description": "Write content to a file. Creates the file if it doesn't exist, overwrites if it does.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Path to the file to write (relative or absolute)"
                            },
                            "content": {
                                "type": "string",
                                "description": "Content to write to the file"
                            }
                        },
                        "required": ["path", "content"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "list_files",
                    "description": "List files and directories in a directory.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Path to the directory to list (relative or absolute)"
                            }
                        },
                        "required": ["path"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "execute_bash",
                    "description": "Execute a bash command and return the output. Use for running scripts, python commands, etc.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "command": {
                                "type": "string",
                                "description": "The bash command to execute"
                            }
                        },
                        "required": ["command"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "create_directory",
                    "description": "Create a directory. Creates parent directories if needed.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Path to the directory to create (relative or absolute)"
                            }
                        },
                        "required": ["path"]
                    }
                }
            }
        ]

    async def execute_tool(self, tool_name: str, args: Dict[str, Any]) -> str:
        """Execute a tool by name

        Args:
            tool_name: Name of the tool to execute
            args: Tool arguments

        Returns:
            Tool execution result as string
        """
        if tool_name not in self.tools:
            return f"Error: Unknown tool '{tool_name}'"

        try:
            handler = self.tools[tool_name]
            result = await handler(**args)
            return result
        except Exception as e:
            return f"Error executing {tool_name}: {str(e)}"

    def _resolve_path(self, path: str) -> Path:
        """Resolve a path relative to working directory

        Args:
            path: Path to resolve (relative or absolute)

        Returns:
            Resolved Path object
        """
        path_obj = Path(path)
        if not path_obj.is_absolute():
            path_obj = self.working_directory / path_obj
        return path_obj.resolve()

    async def _read_file(self, path: str) -> str:
        """Read file contents

        Args:
            path: Path to file

        Returns:
            File contents as string
        """
        file_path = self._resolve_path(path)

        if not file_path.exists():
            return f"Error: File not found: {path}"

        if not file_path.is_file():
            return f"Error: Not a file: {path}"

        try:
            # Try reading as text first
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return f"File: {path}\n\n{content}"
        except UnicodeDecodeError:
            # If text fails, read as binary and return info
            size = file_path.stat().st_size
            return f"File: {path}\n\nBinary file ({size} bytes). Cannot display contents."

    async def _write_file(self, path: str, content: str) -> str:
        """Write content to file

        Args:
            path: Path to file
            content: Content to write

        Returns:
            Success message
        """
        file_path = self._resolve_path(path)

        # Create parent directories if needed
        file_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return f"Successfully wrote to: {path}"
        except Exception as e:
            return f"Error writing file: {str(e)}"

    async def _list_files(self, path: str) -> str:
        """List files in directory

        Args:
            path: Path to directory

        Returns:
            List of files and directories
        """
        dir_path = self._resolve_path(path)

        if not dir_path.exists():
            return f"Error: Directory not found: {path}"

        if not dir_path.is_dir():
            return f"Error: Not a directory: {path}"

        try:
            items = []
            for item in sorted(dir_path.iterdir()):
                if item.is_dir():
                    items.append(f"[DIR]  {item.name}/")
                else:
                    size = item.stat().st_size
                    items.append(f"[FILE] {item.name} ({size} bytes)")

            if not items:
                return f"Directory: {path}\n\n(empty)"

            return f"Directory: {path}\n\n" + "\n".join(items)
        except Exception as e:
            return f"Error listing directory: {str(e)}"

    async def _create_directory(self, path: str) -> str:
        """Create directory

        Args:
            path: Path to directory

        Returns:
            Success message
        """
        dir_path = self._resolve_path(path)

        try:
            dir_path.mkdir(parents=True, exist_ok=True)
            return f"Successfully created directory: {path}"
        except Exception as e:
            return f"Error creating directory: {str(e)}"

    async def _execute_bash(self, command: str) -> str:
        """Execute bash command

        Args:
            command: Command to execute

        Returns:
            Command output (stdout and stderr)
        """
        try:
            # Execute command in working directory
            result = subprocess.run(
                command,
                shell=True,
                cwd=str(self.working_directory),
                capture_output=True,
                text=True,
                timeout=60  # 60 second timeout
            )

            output = []
            if result.stdout:
                output.append(f"STDOUT:\n{result.stdout}")
            if result.stderr:
                output.append(f"STDERR:\n{result.stderr}")

            output.append(f"\nReturn code: {result.returncode}")

            if not result.stdout and not result.stderr:
                return f"Command executed successfully (no output)\nReturn code: {result.returncode}"

            return "\n\n".join(output)

        except subprocess.TimeoutExpired:
            return "Error: Command timed out (60 second limit)"
        except Exception as e:
            return f"Error executing command: {str(e)}"
