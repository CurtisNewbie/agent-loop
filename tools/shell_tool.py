"""Shell Tool - Execute shell commands safely."""
import asyncio
import subprocess
from typing import Optional
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field


class ShellInput(BaseModel):
    """Input for shell command execution."""
    command: str = Field(description="Shell command to execute")
    timeout: Optional[int] = Field(default=30, description="Timeout in seconds")
    cwd: Optional[str] = Field(default=None, description="Working directory")


def execute_shell(command: str, timeout: int = 30, cwd: Optional[str] = None) -> str:
    """Execute a shell command synchronously.
    
    Args:
        command: Shell command to execute
        timeout: Maximum execution time in seconds
        cwd: Working directory for command execution
        
    Returns:
        Command output (stdout + stderr)
    """
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd
        )
        
        output = ""
        if result.stdout:
            output += result.stdout
        if result.stderr:
            output += f"\n[stderr]\n{result.stderr}"
        
        output += f"\n[exit code: {result.returncode}]"
        return output
        
    except subprocess.TimeoutExpired:
        return f"Error: Command timed out after {timeout} seconds"
    except Exception as e:
        return f"Error: {str(e)}"


async def execute_shell_async(command: str, timeout: int = 30, cwd: Optional[str] = None) -> str:
    """Execute a shell command asynchronously.
    
    Args:
        command: Shell command to execute
        timeout: Maximum execution time in seconds
        cwd: Working directory for command execution
        
    Returns:
        Command output (stdout + stderr)
    """
    try:
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd
        )
        
        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=timeout
        )
        
        output = ""
        if stdout:
            output += stdout.decode()
        if stderr:
            output += f"\n[stderr]\n{stderr.decode()}"
        
        output += f"\n[exit code: {process.returncode}]"
        return output
        
    except asyncio.TimeoutError:
        try:
            process.kill()
        except:
            pass
        return f"Error: Command timed out after {timeout} seconds"
    except Exception as e:
        return f"Error: {str(e)}"


# Create the shell tool
shell_tool = StructuredTool(
    name="bash",
    description="Execute shell commands (use with caution). Returns stdout, stderr, and exit code.",
    args_schema=ShellInput,
    func=execute_shell,
    coroutine=execute_shell_async
)

__all__ = ["shell_tool", "ShellInput", "execute_shell", "execute_shell_async"]
