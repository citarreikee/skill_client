"""
LLM Client for AI Model Communication
Supports OpenAI-compatible APIs with tool calling
"""

import os
import json
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class LLMClient:
    """Generic LLM client with tool calling support"""

    def __init__(
        self,
        model: str = "gpt-4",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        provider: str = "openai"
    ):
        """Initialize LLM client

        Args:
            model: Model name
            api_key: API key (defaults to env var)
            base_url: Base URL for API (defaults to provider default)
            provider: Provider name (openai, deepseek, anthropic, etc.)
        """
        self.model = model
        self.provider = provider

        # Get API key from parameter or environment
        if api_key:
            self.api_key = api_key
        else:
            # Try provider-specific env vars
            env_key_map = {
                "openai": "OPENAI_API_KEY",
                "deepseek": "DEEPSEEK_API_KEY",
                "anthropic": "ANTHROPIC_API_KEY"
            }
            env_key = env_key_map.get(provider, "API_KEY")
            self.api_key = os.getenv(env_key)

        if not self.api_key:
            raise ValueError(f"API key not found for provider: {provider}")

        # Set base URL
        if base_url:
            self.base_url = base_url
        else:
            # Provider defaults
            url_map = {
                "openai": "https://api.openai.com/v1",
                "deepseek": "https://api.deepseek.com/v1",
                "anthropic": "https://api.anthropic.com"
            }
            self.base_url = url_map.get(provider, "https://api.openai.com/v1")

        # Initialize client (lazy loading)
        self.client = None
        self._init_client()

        # Tool executor (will be set by skill system)
        self.tool_executor = None

    def _init_client(self):
        """Initialize the API client"""
        try:
            from openai import OpenAI
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
        except ImportError:
            raise ImportError(
                "OpenAI package not installed. "
                "Install with: pip install openai"
            )

    def set_tool_executor(self, executor):
        """Set tool executor for handling tool calls

        Args:
            executor: Tool executor instance
        """
        self.tool_executor = executor

    async def chat(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """Send chat request and handle tool calls

        Args:
            messages: List of message dicts with role and content
            tools: Optional list of tool definitions

        Returns:
            List of response messages (may include tool calls and results)
        """
        if not self.client:
            raise RuntimeError("Client not initialized")

        try:
            # Build API parameters
            api_params = {
                "model": self.model,
                "messages": messages,
            }

            # Add tools if available
            if tools and len(tools) > 0:
                api_params["tools"] = tools
                api_params["parallel_tool_calls"] = True

            # Call API
            completion = self.client.chat.completions.create(**api_params)

            # Parse response
            response_messages = []
            choice = completion.choices[0]
            message = choice.message

            # Build assistant message
            assistant_msg = {
                "role": "assistant",
                "content": message.content
            }

            # Print response
            if message.content:
                print(f"\n{'='*60}")
                print("💭 LLM Response:")
                print(f"{'='*60}")
                print(message.content)
                print(f"{'='*60}\n")

            # Check for tool calls
            if message.tool_calls:
                print(f"\n{'='*60}")
                print("🔧 Tool Calls:")
                print(f"{'='*60}")
                for tc in message.tool_calls:
                    print(f"  → {tc.function.name}")
                    try:
                        args = json.loads(tc.function.arguments)
                        print(f"    Args: {json.dumps(args, indent=6)}")
                    except:
                        print(f"    Args: {tc.function.arguments}")
                print(f"{'='*60}\n")

                # Convert tool calls to dict format
                tool_calls_list = []
                for tc in message.tool_calls:
                    tool_calls_list.append({
                        "id": tc.id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    })
                assistant_msg["tool_calls"] = tool_calls_list

                # Add assistant message with tool calls
                response_messages.append(assistant_msg)

                # Don't execute tools here - let the caller handle them
                # (BaseAgent handles use_skill tool specially)
            else:
                # No tool calls
                response_messages.append(assistant_msg)

            return response_messages

        except Exception as e:
            print(f"❌ API Error: {e}")
            return [{
                "role": "assistant",
                "content": f"Error: {str(e)}"
            }]

    async def _execute_tool_calls(
        self,
        tool_calls: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Execute tool calls using tool executor

        Args:
            tool_calls: List of tool call dicts

        Returns:
            List of tool result messages
        """
        if not self.tool_executor:
            # No tool executor set, return error messages
            return [{
                "role": "tool",
                "tool_call_id": tc.get("id"),
                "name": tc.get("function", {}).get("name", "unknown"),
                "content": "Error: No tool executor configured"
            } for tc in tool_calls]

        tool_responses = []

        for tool_call in tool_calls:
            tool_call_id = tool_call.get("id")
            func_info = tool_call.get("function")

            if not func_info or not tool_call_id:
                continue

            function_name = func_info.get("name")
            arguments_str = func_info.get("arguments", "{}")

            try:
                # Parse arguments
                args = json.loads(arguments_str) if arguments_str.strip() else {}
            except json.JSONDecodeError as e:
                error_msg = f"Failed to parse arguments: {e}"
                tool_responses.append({
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "name": function_name,
                    "content": error_msg
                })
                continue

            try:
                # Execute tool via executor
                result = await self.tool_executor.execute_tool(
                    function_name,
                    args
                )

                # Print result
                print(f"\n{'─'*60}")
                print(f"✅ Tool Result: {function_name}")
                print(f"{'─'*60}")
                result_str = str(result)
                if len(result_str) > 300:
                    print(f"{result_str[:300]}... (truncated)")
                else:
                    print(result_str)
                print(f"{'─'*60}\n")

                tool_responses.append({
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "name": function_name,
                    "content": str(result)
                })

            except Exception as e:
                error_msg = f"Error executing {function_name}: {str(e)}"
                print(f"\n{'─'*60}")
                print(f"❌ Tool Error: {function_name}")
                print(f"{'─'*60}")
                print(error_msg)
                print(f"{'─'*60}\n")

                tool_responses.append({
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "name": function_name,
                    "content": error_msg
                })

        return tool_responses

