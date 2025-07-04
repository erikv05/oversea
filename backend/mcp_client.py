import httpx
import json
from typing import Dict, List, Any, Optional
import asyncio
from datetime import datetime

class MCPClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/') + '/mcp'
        self.client = httpx.AsyncClient(timeout=30.0)
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
            
            print(f"Response status: {response.status_code}")
            print(f"Response headers: {response.headers}")
            print(f"Response text: {response.text[:500]}")
            
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
            response = await self.client.post(
                self.base_url,
                json={
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {
                        "name": tool_name,
                        "arguments": arguments
                    },
                    "id": 2
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
                                if "result" in data:
                                    return data["result"]
                                elif "error" in data:
                                    print(f"MCP error: {data['error']}")
                                    return {"error": data["error"]}
                            except json.JSONDecodeError:
                                continue
                else:
                    # Regular JSON response
                    result = response.json()
                    if "result" in result:
                        return result["result"]
                    elif "error" in result:
                        print(f"MCP error: {result['error']}")
                        return {"error": result["error"]}
            else:
                print(f"Failed to call MCP tool: {response.status_code}")
                return {"error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            print(f"Error calling MCP tool: {str(e)}")
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