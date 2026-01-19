"""
Base Agent Class
Simplified base class for skill-based agents with progressive loading
"""

import json
from typing import List, Dict, Optional, Any, Tuple
from .base_tools import BaseToolExecutor


class BaseAgent:
    """Base class for all agents with progressive skill loading"""

    def __init__(
        self,
        system_prompt: str,
        model: str = "gpt-4",
        max_rounds: int = 100,
        working_directory: Optional[str] = None
    ):
        """Initialize base agent

        Args:
            system_prompt: System prompt for this agent
            model: Model name to use
            max_rounds: Maximum reasoning rounds to prevent infinite loops
            working_directory: Working directory for base tools (defaults to cwd)
        """
        self.system_prompt = system_prompt
        self.model = model
        self.max_rounds = max_rounds
        self.agent_name = self.__class__.__name__

        # Message history for context
        self.messages: List[Dict[str, Any]] = []

        # Skill loader (set externally)
        self.skill_loader = None

        # Activated skills (Level 2 - full SKILL.md loaded)
        self.activated_skills: Dict[str, str] = {}

        # LLM client (to be set)
        self.llm_client = None

        # Base tool executor for file operations, bash execution, etc.
        self.base_tool_executor = BaseToolExecutor(working_directory)

    def set_llm_client(self, llm_client):
        """Set LLM client for API communication

        Args:
            llm_client: LLM client instance
        """
        self.llm_client = llm_client

    def set_skill_loader(self, skill_loader):
        """Set skill loader for progressive skill loading

        Args:
            skill_loader: SkillLoader instance
        """
        self.skill_loader = skill_loader

    def activate_skill(self, skill_name: str) -> bool:
        """Activate a skill (Level 2 loading)

        Args:
            skill_name: Name of the skill to activate

        Returns:
            True if activated successfully, False otherwise
        """
        if not self.skill_loader:
            print("❌ No skill loader set")
            return False

        # Check if already activated
        if skill_name in self.activated_skills:
            print(f"ℹ️  Skill already activated: {skill_name}")
            return True

        # Load full SKILL.md content
        content = self.skill_loader.activate_skill(skill_name)
        if content:
            self.activated_skills[skill_name] = content
            return True

        return False

    def get_available_skills(self) -> List[Dict[str, str]]:
        """Get list of available skills (Level 1 data only)

        Returns:
            List of skill metadata (name, description)
        """
        if not self.skill_loader:
            return []

        skills = []
        for skill_name in self.skill_loader.list_skills():
            desc = self.skill_loader.get_skill_description(skill_name)
            skills.append({
                "name": skill_name,
                "description": desc
            })
        return skills

    def _get_use_skill_tool(self) -> Dict[str, Any]:
        """Get the use_skill tool definition for AI to request skills

        Returns:
            Tool definition in OpenAI format
        """
        return {
            "type": "function",
            "function": {
                "name": "use_skill",
                "description": "Activate a skill to access its full capabilities. Call this when you need to use a specific skill to complete the user's request.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "skill_name": {
                            "type": "string",
                            "description": "The name of the skill to activate (e.g., 'pptx', 'canvas-design')"
                        },
                        "reason": {
                            "type": "string",
                            "description": "Brief explanation of why you need this skill"
                        }
                    },
                    "required": ["skill_name", "reason"]
                }
            }
        }

    async def _handle_use_skill(self, skill_name: str, reason: str) -> str:
        """Handle skill activation request from AI

        Args:
            skill_name: Name of skill to activate
            reason: Why the AI needs this skill

        Returns:
            Result message
        """
        print(f"\n🤖 AI requests skill: {skill_name}")
        print(f"   Reason: {reason}")

        if self.activate_skill(skill_name):
            return f"Skill '{skill_name}' activated successfully. You now have access to its full instructions and capabilities."
        else:
            return f"Failed to activate skill '{skill_name}'. Please check if the skill exists."

    def _parse_tool_args(
        self,
        arguments: Any,
        function_name: str
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """Parse tool call arguments safely.

        Returns:
            (args, error_message) tuple. If error_message is not None, args is None.
        """
        if arguments is None:
            return {}, None

        if isinstance(arguments, dict):
            return arguments, None

        if not isinstance(arguments, str):
            return None, (
                f"Error: Tool '{function_name}' arguments must be a JSON string, "
                f"got {type(arguments).__name__}."
            )

        if not arguments.strip():
            return {}, None

        try:
            return json.loads(arguments), None
        except json.JSONDecodeError:
            try:
                return json.loads(arguments, strict=False), None
            except json.JSONDecodeError as e:
                snippet = arguments.strip()
                if len(snippet) > 200:
                    snippet = snippet[:200] + "...(truncated)"
                return None, (
                    f"Error: Invalid JSON arguments for tool '{function_name}': {e}. "
                    f"Raw: {snippet}"
                )

    async def chat(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """Chat with the agent using ReAct loop

        Only activated skills are injected into the prompt (Level 2).

        Args:
            messages: List of message dicts with role and content

        Returns:
            Final assistant message dict
        """
        if not self.llm_client:
            raise RuntimeError("LLM client not set. Call set_llm_client() first")

        # Build full message list with system prompt
        full_messages = [
            {"role": "system", "content": self.system_prompt}
        ]

        # Add Level 1 skill metadata (so AI knows what skills are available)
        if self.skill_loader:
            available_skills = self.get_available_skills()
            if available_skills:
                skill_list = "\n\n## Available Skills (Level 1)\n\n"
                skill_list += "You have access to the following skills. To use a skill, call the use_skill function.\n\n"
                for skill in available_skills:
                    skill_list += f"- **{skill['name']}**: {skill['description']}\n"
                full_messages[0]["content"] += skill_list

        # Add activated skill instructions (Level 2 - full content)
        if self.activated_skills:
            skill_instructions = "\n\n## Activated Skills (Level 2)\n\n"
            for skill_name, skill_content in self.activated_skills.items():
                skill_instructions += f"### Skill: {skill_name}\n\n"
                skill_instructions += skill_content + "\n\n"

            # Append to system prompt
            full_messages[0]["content"] += skill_instructions

        full_messages.extend(messages)

        round_count = 0

        # ReAct loop: Loop until we get final response (no tool calls)
        while round_count < self.max_rounds:
            round_count += 1

            # Provide use_skill tool so AI can request skills
            tools = [self._get_use_skill_tool()] if self.skill_loader else []

            # Add base tools (file operations, bash execution, etc.)
            tools.extend(self.base_tool_executor.get_tool_definitions())

            # Call LLM
            response_messages = await self.llm_client.chat(
                full_messages,
                tools=tools
            )

            # Add response messages to history
            full_messages.extend(response_messages)

            # Check if last message is final assistant response
            last_message = full_messages[-1]

            # Handle tool calls (skill activation requests and base tools)
            if last_message.get("role") == "assistant" and "tool_calls" in last_message:
                # Process tool calls
                for tool_call in last_message["tool_calls"]:
                    function_name = tool_call["function"]["name"]

                    args, parse_error = self._parse_tool_args(
                        tool_call.get("function", {}).get("arguments"),
                        function_name
                    )

                    if parse_error:
                        result = parse_error
                    elif function_name == "use_skill":
                        # Handle skill activation
                        result = await self._handle_use_skill(
                            args.get("skill_name", ""),
                            args.get("reason", "")
                        )
                    else:
                        # Handle base tool execution
                        result = await self.base_tool_executor.execute_tool(
                            function_name,
                            args
                        )

                    # Add tool result to messages
                    full_messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "name": function_name,
                        "content": result
                    })
                # Continue loop to process with tool results
                continue

            if last_message.get("role") == "assistant":
                # Got final response
                return last_message

        # Max rounds reached
        return full_messages[-1] if full_messages else {
            "role": "assistant",
            "content": "Error: Max reasoning rounds reached"
        }

    async def process(self, prompt: str) -> str:
        """Process a prompt and return response

        Args:
            prompt: User prompt/task description

        Returns:
            Agent response as string
        """
        # Convert prompt to messages
        messages = [{"role": "user", "content": prompt}]

        # Call chat
        response = await self.chat(messages)

        # Extract content
        content = response.get("content", "")

        return content
