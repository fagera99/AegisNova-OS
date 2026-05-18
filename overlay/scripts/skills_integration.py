#!/usr/bin/env python3
"""
AegisNova OS — Skills Integration for Model Manager
====================================================
Integrates awesome-agent-skills with the AI model manager.
Auto-selects relevant skills based on query context.

Usage:
    from skills_integration import SkillsIntegration
    skills = SkillsIntegration()
    relevant = skills.find_skills("How to detect SQL injection?", category="security")
"""

import json
import os
import re
from typing import List, Dict, Optional, Any
from dataclasses import dataclass

SKILLS_DIR = "/opt/aegisnova/skills/aegisnova"
INDEX_FILE = f"{SKILLS_DIR}/index.json"

@dataclass
class SkillMatch:
    name: str
    category: str
    subcategory: str
    path: str
    relevance_score: float
    description: str = ""

class SkillsIntegration:
    """Integrates agent skills with AI model manager."""
    
    def __init__(self):
        self.skills_dir = SKILLS_DIR
        self.index = self._load_index()
        self.skill_keywords = self._build_keyword_index()
    
    def _load_index(self) -> Dict[str, Any]:
        """Load skills index."""
        if os.path.exists(INDEX_FILE):
            with open(INDEX_FILE, 'r') as f:
                return json.load(f)
        return {}
    
    def _build_keyword_index(self) -> Dict[str, List[str]]:
        """Build keyword-to-skill mapping."""
        keywords = {
            # Security keywords
            "sql injection": ["vibesec", "static-analysis", "semgrep-rule-creator"],
            "xss": ["vibesec", "static-analysis"],
            "csrf": ["vibesec"],
            "vulnerability": ["static-analysis", "variant-analysis", "semgrep-rule-creator"],
            "pentest": ["burpsuite-project-parser", "ffuf-claude-skill"],
            "penetration": ["burpsuite-project-parser", "ffuf-claude-skill"],
            "scan": ["burpsuite-project-parser", "ffuf-claude-skill", "insecure-defaults"],
            "audit": ["audit-context-building", "clawsec", "static-analysis"],
            "forensic": ["rootly-incident-responder"],
            "incident": ["rootly-incident-responder", "sentry-workflow"],
            "monitor": ["sentry-workflow", "dd-logs", "dd-monitors", "canary"],
            "log": ["dd-logs", "sentry-workflow"],
            "alert": ["sentry-create-alert", "dd-monitors"],
            "smart contract": ["building-secure-contracts", "entry-point-analyzer"],
            "blockchain": ["building-secure-contracts", "entry-point-analyzer"],
            "crypto": ["constant-time-analysis", "azure-keyvault"],
            "authentication": ["auth0-mfa", "auth0-quickstart", "better-auth/twoFactor"],
            "mfa": ["auth0-mfa", "better-auth/twoFactor"],
            "identity": ["auth0-migration", "entra-agent-id"],
            "threat model": ["cso", "security-threat-model"],
            "owasp": ["cso", "vibesec"],
            "fuzz": ["ffuf-claude-skill", "testing-handbook-skills"],
            "malware": ["firebase-apk-scanner"],
            "android": ["firebase-apk-scanner"],
            "secret": ["varlock-claude-skill", "insecure-defaults"],
            "harden": ["insecure-defaults", "sharp-edges", "defense-in-depth"],
            "secure coding": ["vibesec", "security-best-practices"],
            "code review": ["differential-review", "sentry-code-review"],
            "static analysis": ["static-analysis", "semgrep-rule-creator"],
            "semgrep": ["semgrep-rule-creator", "semgrep-rule-variant-creator"],
            "codeql": ["static-analysis"],
            
            # Design keywords
            "design": ["frontend-design", "canvas-design", "design-md"],
            "ui": ["frontend-design", "react-components", "shadcn-ui"],
            "ux": ["frontend-design", "web-design-guidelines"],
            "frontend": ["frontend-design", "react-components", "react-best-practices"],
            "react": ["react-components", "react-best-practices"],
            "component": ["react-components", "composition-patterns", "shadcn-ui"],
            "theme": ["theme-factory", "brand-guidelines"],
            "dashboard": ["frontend-design", "react-components"],
            "visualization": ["algorithmic-art", "canvas-design"],
            "report": ["canvas-design", "web-artifacts-builder"],
            "prototype": ["stitch-loop", "react-components"],
            "interface": ["frontend-design", "web-design-guidelines"],
        }
        return keywords
    
    def find_skills(
        self,
        query: str,
        category: Optional[str] = None,
        max_results: int = 5
    ) -> List[SkillMatch]:
        """
        Find relevant skills for a query.
        
        Args:
            query: User query
            category: Filter by category (security/design)
            max_results: Maximum skills to return
        
        Returns:
            List of SkillMatch objects sorted by relevance
        """
        query_lower = query.lower()
        matches = []
        
        # Score skills based on keyword matches
        skill_scores = {}
        
        for keyword, skill_list in self.skill_keywords.items():
            if keyword in query_lower:
                for skill_name in skill_list:
                    if skill_name not in skill_scores:
                        skill_scores[skill_name] = 0
                    skill_scores[skill_name] += 1
        
        # Also check if skill name is directly mentioned
        all_skills = self._list_all_skills()
        for skill in all_skills:
            if skill['name'].lower() in query_lower:
                if skill['name'] not in skill_scores:
                    skill_scores[skill['name']] = 0
                skill_scores[skill['name']] += 2  # Direct mention = higher score
        
        # Create SkillMatch objects
        for skill_name, score in sorted(skill_scores.items(), key=lambda x: x[1], reverse=True):
            skill_info = self._get_skill_info(skill_name)
            
            if category and skill_info.get('category') != category:
                continue
            
            matches.append(SkillMatch(
                name=skill_name,
                category=skill_info.get('category', 'unknown'),
                subcategory=skill_info.get('subcategory', 'unknown'),
                path=skill_info.get('path', ''),
                relevance_score=min(score / 3.0, 1.0),  # Normalize to 0-1
                description=skill_info.get('description', '')
            ))
        
        return matches[:max_results]
    
    def _list_all_skills(self) -> List[Dict[str, str]]:
        """List all available skills."""
        skills = []
        
        if not os.path.exists(self.skills_dir):
            return skills
        
        for category in ['security', 'design']:
            category_dir = os.path.join(self.skills_dir, category)
            if not os.path.exists(category_dir):
                continue
            
            for subcategory in os.listdir(category_dir):
                subcategory_dir = os.path.join(category_dir, subcategory)
                if not os.path.isdir(subcategory_dir):
                    continue
                
                for skill_file in os.listdir(subcategory_dir):
                    skill_name = skill_file.replace('.md', '').replace('.json', '')
                    skills.append({
                        'name': skill_name,
                        'category': category,
                        'subcategory': subcategory,
                        'path': os.path.join(subcategory_dir, skill_file)
                    })
        
        return skills
    
    def _get_skill_info(self, skill_name: str) -> Dict[str, str]:
        """Get skill information."""
        skills = self._list_all_skills()
        for skill in skills:
            if skill['name'] == skill_name:
                return skill
        return {}
    
    def get_skill_content(self, skill_name: str) -> str:
        """Get skill file content."""
        skill_info = self._get_skill_info(skill_name)
        path = skill_info.get('path', '')
        
        if path and os.path.exists(path):
            with open(path, 'r') as f:
                return f.read()
        return f"Skill not found: {skill_name}"
    
    def format_skill_prompt(self, skill_name: str, user_query: str) -> str:
        """
        Format a prompt that includes skill instructions.
        
        Args:
            skill_name: Name of the skill to use
            user_query: Original user query
        
        Returns:
            Enhanced prompt with skill context
        """
        skill_content = self.get_skill_content(skill_name)
        
        prompt = f"""[Using Skill: {skill_name}]

{skill_content}

---

User Query: {user_query}

Please apply the above skill guidelines when responding."""
        
        return prompt
    
    def auto_select_skills(
        self,
        query: str,
        context: str = "general"
    ) -> List[str]:
        """
        Automatically select skills based on query and context.
        
        Args:
            query: User query
            context: Context (security_research, design, general)
        
        Returns:
            List of recommended skill names
        """
        category = None
        if context in ['security_research', 'redteam', 'blueteam', 'pentest']:
            category = 'security'
        elif context in ['design', 'frontend', 'ui', 'ux']:
            category = 'design'
        
        matches = self.find_skills(query, category=category, max_results=3)
        return [match.name for match in matches]


# CLI Interface
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="AegisNova Skills Integration")
    parser.add_argument("query", nargs="?", help="Query to find skills for")
    parser.add_argument("--category", "-c", default=None, help="Filter by category")
    parser.add_argument("--max", "-m", type=int, default=5, help="Max results")
    parser.add_argument("--use", "-u", help="Get skill content")
    parser.add_argument("--auto", "-a", action="store_true", help="Auto-select for query")
    parser.add_argument("--context", default="general", help="Context for auto-selection")
    
    args = parser.parse_args()
    
    skills = SkillsIntegration()
    
    if args.use:
        print(skills.get_skill_content(args.use))
    elif args.auto and args.query:
        selected = skills.auto_select_skills(args.query, args.context)
        print("Recommended skills:")
        for skill in selected:
            print(f"  - {skill}")
    elif args.query:
        matches = skills.find_skills(args.query, category=args.category, max_results=args.max)
        print(f"Skills for: {args.query}")
        print("-" * 60)
        for match in matches:
            print(f"\n{match.name} (Relevance: {match.relevance_score:.0%})")
            print(f"  Category: {match.category}/{match.subcategory}")
            if match.description:
                print(f"  Description: {match.description}")
    else:
        parser.print_help()
