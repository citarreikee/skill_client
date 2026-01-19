"""
Skill Loader System - Anthropic Format
Implements level 1-3 progressive content loading
"""

import os
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional


class SkillLoader:
    """Loads and manages skills following Anthropic's format"""

    def __init__(self, skills_directory: str):
        """Initialize skill loader

        Args:
            skills_directory: Path to directory containing skill folders
        """
        self.skills_directory = Path(skills_directory)

        # Level 1: Only name + description (loaded at startup)
        self.skill_metadata: Dict[str, Dict[str, str]] = {}

        # Level 2: Full SKILL.md content (loaded when activated)
        self.skill_content: Dict[str, str] = {}

        # Level 3: Supporting files (loaded on demand)
        self.skill_resources: Dict[str, Dict[str, str]] = {}

        if not self.skills_directory.exists():
            raise ValueError(f"Skills directory not found: {skills_directory}")

    def discover_skills(self) -> Dict[str, Dict[str, str]]:
        """Level 1: Discover skills and load only name + description

        This keeps startup fast while giving context about available skills.

        Returns:
            Dictionary of skill_name -> {name, description, path}
        """
        print(f"\n{'='*60}")
        print("📦 Discovering Skills (Level 1)")
        print(f"{'='*60}")

        # Find all skill folders (containing SKILL.md)
        skill_folders = []
        for item in self.skills_directory.iterdir():
            if item.is_dir():
                skill_file = item / "SKILL.md"
                if skill_file.exists():
                    skill_folders.append(item)

        if not skill_folders:
            print("⚠️  No skill folders found")
            return {}

        for skill_folder in skill_folders:
            try:
                metadata = self._load_skill_metadata(skill_folder)
                if metadata:
                    skill_name = metadata["name"]
                    self.skill_metadata[skill_name] = metadata
                    print(f"  ✓ Discovered: {skill_name}")
                    print(f"    Description: {metadata['description'][:80]}...")
            except Exception as e:
                print(f"  ✗ Failed to load {skill_folder.name}: {e}")

        print(f"{'='*60}")
        print(f"Total skills discovered: {len(self.skill_metadata)}")
        print(f"{'='*60}\n")

        return self.skill_metadata

    def _load_skill_metadata(self, skill_folder: Path) -> Optional[Dict[str, str]]:
        """Load only metadata from SKILL.md frontmatter (Level 1)

        Args:
            skill_folder: Path to skill folder

        Returns:
            Dictionary with name, description, and path
        """
        skill_file = skill_folder / "SKILL.md"
        content = skill_file.read_text(encoding="utf-8")

        # Parse only the YAML frontmatter
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 2:
                frontmatter = yaml.safe_load(parts[1])
                return {
                    "name": frontmatter.get("name", skill_folder.name),
                    "description": frontmatter.get("description", ""),
                    "path": str(skill_folder),
                    "license": frontmatter.get("license", "")
                }

        return None

    def activate_skill(self, skill_name: str) -> Optional[str]:
        """Level 2: Load full SKILL.md content when skill is activated

        Args:
            skill_name: Name of the skill to activate

        Returns:
            Full SKILL.md content as string
        """
        if skill_name not in self.skill_metadata:
            print(f"❌ Skill not found: {skill_name}")
            return None

        # Check if already loaded
        if skill_name in self.skill_content:
            return self.skill_content[skill_name]

        # Load full SKILL.md
        skill_path = Path(self.skill_metadata[skill_name]["path"])
        skill_file = skill_path / "SKILL.md"

        print(f"\n{'='*60}")
        print(f"📖 Activating Skill (Level 2): {skill_name}")
        print(f"{'='*60}")

        try:
            content = skill_file.read_text(encoding="utf-8")

            # Store the full content
            self.skill_content[skill_name] = content

            print(f"  ✓ Loaded: {len(content)} characters")
            print(f"{'='*60}\n")

            return content
        except Exception as e:
            print(f"  ✗ Failed to load: {e}")
            print(f"{'='*60}\n")
            return None

    def load_resource(self, skill_name: str, resource_path: str) -> Optional[str]:
        """Level 3: Load supporting files on demand

        Args:
            skill_name: Name of the skill
            resource_path: Relative path to resource file (e.g., "ooxml.md", "scripts/unpack.py")

        Returns:
            Resource file content as string
        """
        if skill_name not in self.skill_metadata:
            print(f"❌ Skill not found: {skill_name}")
            return None

        skill_path = Path(self.skill_metadata[skill_name]["path"])
        resource_file = skill_path / resource_path

        if not resource_file.exists():
            print(f"❌ Resource not found: {resource_path}")
            return None

        # Initialize cache for this skill if needed
        if skill_name not in self.skill_resources:
            self.skill_resources[skill_name] = {}

        # Check if already loaded
        if resource_path in self.skill_resources[skill_name]:
            return self.skill_resources[skill_name][resource_path]

        print(f"📄 Loading resource (Level 3): {resource_path}")

        try:
            content = resource_file.read_text(encoding="utf-8")
            self.skill_resources[skill_name][resource_path] = content
            print(f"  ✓ Loaded: {len(content)} characters")
            return content
        except Exception as e:
            print(f"  ✗ Failed to load: {e}")
            return None

    def list_skills(self) -> List[str]:
        """Get list of discovered skill names

        Returns:
            List of skill names
        """
        return list(self.skill_metadata.keys())

    def get_skill_description(self, skill_name: str) -> Optional[str]:
        """Get skill description (Level 1 data)

        Args:
            skill_name: Name of the skill

        Returns:
            Skill description or None
        """
        if skill_name in self.skill_metadata:
            return self.skill_metadata[skill_name]["description"]
        return None
