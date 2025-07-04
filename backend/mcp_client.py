import httpx
import json
from typing import Dict, List, Any, Optional
import asyncio
from datetime import datetime

class MCPClient:
    def __init__(self, base_url: str):
        # Ensure the URL ends with /mcp
        if not base_url.endswith('/mcp'):
            self.base_url = base_url.rstrip('/') + '/mcp'
        else:
            self.base_url = base_url
        # Set timeout for MCP operations
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(
                connect=10.0,  # 10 seconds to establish connection
                read=60.0,     # 60 seconds to read response
                write=10.0,    # 10 seconds to write request
                pool=10.0      # 10 seconds to acquire connection from pool
            )
        )
        self.tools = []
        
    async def initialize(self):
        """Initialize connection and discover available tools"""
        try:
            # Discover available tools
            response = await self.client.post(
                self.base_url,
                json={
                    "jsonrpc": "2.0",
                    "method": "tools/list",
                    "params": {},
                    "id": 1
                },
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream"
                }
            )
            
            if response.status_code == 200:
                # Check if response is event-stream
                if 'text/event-stream' in response.headers.get('content-type', ''):
                    # Parse event-stream response
                    lines = response.text.strip().split('\n')
                    for line in lines:
                        if line.startswith('data: '):
                            try:
                                data = json.loads(line[6:])
                                if "result" in data and "tools" in data["result"]:
                                    self.tools = data["result"]["tools"]
                                    break
                            except json.JSONDecodeError:
                                continue
                else:
                    # Regular JSON response
                    result = response.json()
                    if "result" in result and "tools" in result["result"]:
                        self.tools = result["result"]["tools"]
                
                if self.tools:
                    print(f"MCP initialized with {len(self.tools)} tools:")
                    for tool in self.tools:
                        print(f"  - {tool['name']}: {tool.get('description', 'No description')}")
                else:
                    print("No tools found in MCP response")
            else:
                print(f"Failed to initialize MCP: {response.status_code}")
                print(f"Response: {response.text}")
                
        except Exception as e:
            print(f"Error initializing MCP: {str(e)}")
            
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a specific MCP tool"""
        try:
            request_data = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                },
                "id": 2
            }
            try:
                # Try streaming the response instead
                async with self.client.stream(
                    "POST",
                    self.base_url,
                    json=request_data,
                    headers={
                        "Content-Type": "application/json",
                        "Accept": "application/json, text/event-stream"
                    }
                ) as response:
                    if response.status_code != 200:
                        content = await response.aread()
                        return {"error": f"HTTP {response.status_code}: {content}"}
                    
                    # Handle event-stream response
                    if 'text/event-stream' in response.headers.get('content-type', ''):
                        buffer = ""
                        
                        # Read chunks as they arrive
                        async for chunk in response.aiter_bytes():
                            chunk_text = chunk.decode('utf-8')
                            buffer += chunk_text
                            
                            # Process complete lines
                            while '\n' in buffer:
                                line, buffer = buffer.split('\n', 1)
                                line = line.strip()
                                
                                if line.startswith('data: '):
                                    try:
                                        data = json.loads(line[6:])
                                        
                                        if "result" in data:
                                            return data["result"]
                                        elif "error" in data:
                                            # Parse the error message
                                            error_obj = data.get("error", {})
                                            if isinstance(error_obj, dict):
                                                error_msg = error_obj.get("message", str(error_obj))
                                                # Check for missing instructions error
                                                if "instructions" in error_msg and "Required" in error_msg:
                                                    print(f"MCP Error: Missing required 'instructions' parameter")
                                                return {"error": error_msg}
                                            return {"error": str(data["error"])}
                                    except json.JSONDecodeError:
                                        continue
                        
                        return {"error": "No valid response data in stream"}
                    else:
                        # Regular JSON response
                        content = await response.aread()
                        response_text = content.decode('utf-8')
                        
                        try:
                            data = json.loads(response_text)
                            return data.get("result", {"error": "No result in response"})
                        except json.JSONDecodeError:
                            print(f"Failed to parse JSON response: {response_text[:200]}")
                            return {"error": "Invalid JSON response"}
                            
            except httpx.TimeoutException as e:
                print(f"Request timed out: {e}")
                raise
            except Exception as e:
                print(f"Request failed with error: {type(e).__name__}: {e}")
                import traceback
                traceback.print_exc()
                raise
            
                
        except httpx.ReadTimeout:
            print("MCP tool call timed out after 120 seconds")
            return {"error": "The calendar operation is taking longer than expected. It may still complete in the background."}
        except httpx.ConnectTimeout:
            print("Failed to connect to MCP server")
            return {"error": "Unable to connect to the calendar service. Please try again."}
        except Exception as e:
            print(f"Error calling MCP tool: {str(e)}")
            import traceback
            traceback.print_exc()
            return {"error": str(e)}
            
    def get_tools_description(self) -> str:
        """Get a formatted description of available tools for the LLM"""
        if not self.tools:
            return "No tools available."
            
        descriptions = []
        for tool in self.tools:
            desc = f"- {tool['name']}: {tool.get('description', 'No description')}"
            if "inputSchema" in tool and "properties" in tool["inputSchema"]:
                params = []
                for param, schema in tool["inputSchema"]["properties"].items():
                    param_desc = f"{param} ({schema.get('type', 'any')})"
                    if "description" in schema:
                        param_desc += f" - {schema['description']}"
                    params.append(param_desc)
                if params:
                    desc += f"\n  Parameters: {', '.join(params)}"
            descriptions.append(desc)
            
        return "\n".join(descriptions)
        
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()