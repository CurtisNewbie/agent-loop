"""File System Tool - File operations."""
import os
import pathlib
from typing import Optional, List
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field


class ReadFileInput(BaseModel):
    """Input for reading a file."""
    path: str = Field(description="File path to read")
    encoding: Optional[str] = Field(default="utf-8", description="File encoding")


class WriteFileInput(BaseModel):
    """Input for writing a file."""
    path: str = Field(description="File path to write")
    content: str = Field(description="Content to write")
    encoding: Optional[str] = Field(default="utf-8", description="File encoding")
    create_dirs: Optional[bool] = Field(default=True, description="Create parent directories if they don't exist")


class ListDirectoryInput(BaseModel):
    """Input for listing directory contents."""
    path: str = Field(description="Directory path to list")
    recursive: Optional[bool] = Field(default=False, description="List recursively")
    show_hidden: Optional[bool] = Field(default=False, description="Show hidden files")


class DeleteFileInput(BaseModel):
    """Input for deleting a file or directory."""
    path: str = Field(description="File or directory path to delete")
    recursive: Optional[bool] = Field(default=False, description="Delete recursively for directories")


def read_file(path: str, encoding: str = "utf-8") -> str:
    """Read a file.
    
    Args:
        path: File path
        encoding: File encoding
        
    Returns:
        File content
    """
    try:
        with open(path, "r", encoding=encoding) as f:
            return f.read()
    except FileNotFoundError:
        return f"Error: File not found: {path}"
    except IsADirectoryError:
        return f"Error: Path is a directory: {path}"
    except Exception as e:
        return f"Error: {str(e)}"


def write_file(path: str, content: str, encoding: str = "utf-8", create_dirs: bool = True) -> str:
    """Write content to a file.
    
    Args:
        path: File path
        content: Content to write
        encoding: File encoding
        create_dirs: Create parent directories if needed
        
    Returns:
        Success message
    """
    try:
        if create_dirs:
            pathlib.Path(path).parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, "w", encoding=encoding) as f:
            f.write(content)
        
        return f"Successfully wrote {len(content)} bytes to {path}"
    except Exception as e:
        return f"Error: {str(e)}"


def list_directory(path: str, recursive: bool = False, show_hidden: bool = False) -> str:
    """List directory contents.
    
    Args:
        path: Directory path
        recursive: List recursively
        show_hidden: Show hidden files
        
    Returns:
        Directory listing
    """
    try:
        path_obj = pathlib.Path(path)
        
        if not path_obj.exists():
            return f"Error: Path does not exist: {path}"
        
        if not path_obj.is_dir():
            return f"Error: Path is not a directory: {path}"
        
        items = []
        
        if recursive:
            for item in path_obj.rglob("*"):
                if not show_hidden and any(part.startswith(".") for part in item.parts):
                    continue
                item_type = "DIR " if item.is_dir() else "FILE"
                items.append(f"{item_type} {item}")
        else:
            for item in path_obj.iterdir():
                if not show_hidden and item.name.startswith("."):
                    continue
                item_type = "DIR " if item.is_dir() else "FILE"
                items.append(f"{item_type} {item.name}")
        
        if not items:
            return f"Directory is empty: {path}"
        
        return "\n".join(items)
        
    except Exception as e:
        return f"Error: {str(e)}"


def delete_file(path: str, recursive: bool = False) -> str:
    """Delete a file or directory.
    
    Args:
        path: File or directory path
        recursive: Delete recursively for directories
        
    Returns:
        Success message
    """
    try:
        path_obj = pathlib.Path(path)
        
        if not path_obj.exists():
            return f"Error: Path does not exist: {path}"
        
        if path_obj.is_file():
            path_obj.unlink()
            return f"Successfully deleted file: {path}"
        elif path_obj.is_dir():
            if recursive:
                import shutil
                shutil.rmtree(path)
                return f"Successfully deleted directory (recursive): {path}"
            else:
                try:
                    path_obj.rmdir()
                    return f"Successfully deleted empty directory: {path}"
                except OSError as e:
                    return f"Error: Directory not empty, use recursive=True: {e}"
        else:
            return f"Error: Unknown path type: {path}"
            
    except Exception as e:
        return f"Error: {str(e)}"


# Create the file system tools
read_file_tool = StructuredTool(
    name="read_file",
    description="Read a file's contents.",
    args_schema=ReadFileInput,
    func=read_file
)

write_file_tool = StructuredTool(
    name="write_file",
    description="Write content to a file. Creates parent directories by default.",
    args_schema=WriteFileInput,
    func=write_file
)

list_directory_tool = StructuredTool(
    name="list_directory",
    description="List files and directories. Supports recursive listing.",
    args_schema=ListDirectoryInput,
    func=list_directory
)

delete_file_tool = StructuredTool(
    name="delete_file",
    description="Delete a file or directory.",
    args_schema=DeleteFileInput,
    func=delete_file
)

__all__ = [
    "read_file_tool",
    "write_file_tool",
    "list_directory_tool",
    "delete_file_tool",
    "ReadFileInput",
    "WriteFileInput",
    "ListDirectoryInput",
    "DeleteFileInput",
    "read_file",
    "write_file",
    "list_directory",
    "delete_file"
]
