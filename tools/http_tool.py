"""HTTP Tool - Make HTTP requests."""
import asyncio
import json
from typing import Optional, Dict, Any
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field


class HTTPInput(BaseModel):
    """Input for HTTP requests."""
    method: str = Field(description="HTTP method (GET, POST, PUT, DELETE, PATCH)")
    url: str = Field(description="Request URL")
    headers: Optional[Dict[str, str]] = Field(default=None, description="Request headers")
    body: Optional[Dict[str, Any]] = Field(default=None, description="Request body (for POST/PUT/PATCH)")
    timeout: Optional[int] = Field(default=30, description="Timeout in seconds")


async def make_http_request(
    method: str,
    url: str,
    headers: Optional[Dict[str, str]] = None,
    body: Optional[Dict[str, Any]] = None,
    timeout: int = 30
) -> str:
    """Make an HTTP request asynchronously.
    
    Args:
        method: HTTP method (GET, POST, PUT, DELETE, PATCH)
        url: Request URL
        headers: Request headers
        body: Request body (for POST/PUT/PATCH)
        timeout: Maximum execution time in seconds
        
    Returns:
        Response body, status code, and headers
    """
    import httpx
    
    method = method.upper()
    
    if headers is None:
        headers = {}
    
    # Set default Content-Type for POST/PUT/PATCH
    if method in ["POST", "PUT", "PATCH"] and body and "Content-Type" not in headers:
        headers["Content-Type"] = "application/json"
    
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            if method == "GET":
                response = await client.get(url, headers=headers)
            elif method == "POST":
                response = await client.post(url, headers=headers, json=body)
            elif method == "PUT":
                response = await client.put(url, headers=headers, json=body)
            elif method == "DELETE":
                response = await client.delete(url, headers=headers)
            elif method == "PATCH":
                response = await client.patch(url, headers=headers, json=body)
            else:
                return f"Error: Unsupported HTTP method: {method}"
            
            # Format response
            result = {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "body": response.text
            }
            
            # Try to parse JSON response
            try:
                result["json"] = response.json()
            except:
                pass
            
            return json.dumps(result, indent=2)
            
        except httpx.TimeoutException:
            return f"Error: Request timed out after {timeout} seconds"
        except httpx.HTTPStatusError as e:
            return f"Error: HTTP status error - {e}"
        except Exception as e:
            return f"Error: {str(e)}"


def make_http_request_sync(
    method: str,
    url: str,
    headers: Optional[Dict[str, str]] = None,
    body: Optional[Dict[str, Any]] = None,
    timeout: int = 30
) -> str:
    """Make an HTTP request synchronously."""
    import httpx
    
    method = method.upper()
    
    if headers is None:
        headers = {}
    
    if method in ["POST", "PUT", "PATCH"] and body and "Content-Type" not in headers:
        headers["Content-Type"] = "application/json"
    
    try:
        with httpx.Client(timeout=timeout) as client:
            if method == "GET":
                response = client.get(url, headers=headers)
            elif method == "POST":
                response = client.post(url, headers=headers, json=body)
            elif method == "PUT":
                response = client.put(url, headers=headers, json=body)
            elif method == "DELETE":
                response = client.delete(url, headers=headers)
            elif method == "PATCH":
                response = client.patch(url, headers=headers, json=body)
            else:
                return f"Error: Unsupported HTTP method: {method}"
            
            result = {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "body": response.text
            }
            
            try:
                result["json"] = response.json()
            except:
                pass
            
            return json.dumps(result, indent=2)
            
    except httpx.TimeoutException:
        return f"Error: Request timed out after {timeout} seconds"
    except httpx.HTTPStatusError as e:
        return f"Error: HTTP status error - {e}"
    except Exception as e:
        return f"Error: {str(e)}"


# Create the HTTP tool
http_tool = StructuredTool(
    name="http_request",
    description="Make HTTP requests (GET, POST, PUT, DELETE, PATCH). Returns status code, headers, and body.",
    args_schema=HTTPInput,
    func=make_http_request_sync,
    coroutine=make_http_request
)

__all__ = ["http_tool", "HTTPInput", "make_http_request", "make_http_request_sync"]
