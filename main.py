"""
Skill Client System - Main Entry Point
Demonstrates Anthropic-style progressive skill loading (Level 1-3)
"""

import asyncio
import os
from pathlib import Path

from core.base_agent import BaseAgent
from core.llm_client import LLMClient
from core.skill_loader import SkillLoader


async def main():
    """Main entry point demonstrating progressive skill loading"""
    print("\n" + "="*60)
    print("🚀 Skill Client System (Anthropic Format)")
    print("="*60 + "\n")

    # Get project root
    project_root = Path(__file__).parent
    skills_dir = project_root / "skills"

    # ========================================
    # LEVEL 1: DISCOVERY
    # Load only skill names and descriptions
    # ========================================
    print("LEVEL 1: Discovering Skills...")
    skill_loader = SkillLoader(str(skills_dir))
    skill_metadata = skill_loader.discover_skills()

    if not skill_metadata:
        print("❌ No skills found. Please add skill folders to skills/")
        return

    # ========================================
    # Initialize LLM Client
    # ========================================
    print("\nInitializing LLM Client...")

    # Check for API key
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        print("⚠️  No API key found. Set OPENAI_API_KEY or DEEPSEEK_API_KEY")
        print("   For testing, create a .env file with your API key")
        return

    # Determine provider
    provider = "deepseek" if os.getenv("DEEPSEEK_API_KEY") else "openai"
    model = "deepseek-chat" if provider == "deepseek" else "gpt-4"

    llm_client = LLMClient(model=model, provider=provider)
    print(f"  ✓ Using provider: {provider}")
    print(f"  ✓ Using model: {model}")

    # ========================================
    # Create Base Agent
    # ========================================
    print("\nCreating Base Agent...")
    agent = BaseAgent(
        system_prompt="You are a helpful AI assistant with access to skills.",
        model=model
    )
    agent.set_llm_client(llm_client)
    agent.set_skill_loader(skill_loader)
    print("  ✓ Agent ready")

    # ========================================
    # Show Available Skills (Informational)
    # ========================================
    print("\n" + "="*60)
    print("Available Skills (Level 1)")
    print("="*60)
    print("\nThe AI can automatically activate these skills when needed:")
    for skill_name, metadata in skill_metadata.items():
        print(f"\n• {skill_name}")
        print(f"  {metadata['description'][:120]}...")

    print("\n" + "="*60)
    print("✅ System Ready!")
    print("="*60)
    print("\nThe AI will automatically choose and activate skills based on your requests.")

    # ========================================
    # Interactive Loop
    # ========================================
    print("\nType your request or 'quit' to exit\n")

    while True:
        try:
            user_input = input("You: ").strip()

            if user_input.lower() in ['quit', 'exit', 'q']:
                print("\n👋 Goodbye!")
                break

            if not user_input:
                continue

            # Process user input (AI will automatically activate skills if needed)
            print("\n" + "-"*60)
            response = await agent.process(user_input)
            print("-"*60)
            print(f"\nAssistant: {response}\n")

        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}\n")


if __name__ == "__main__":
    asyncio.run(main())


