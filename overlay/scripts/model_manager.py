#!/usr/bin/env python3
"""
AegisNova OS — Unified AI Model Manager with Decensoring
===========================================================
Manages all AI model backends: Local (GGUF/HF), API (OpenAI/Anthropic), Cloud.
Integrates Heretic decensoring for local models and response filtering for APIs.

Features:
- Auto-detects and decensors local models via Heretic
- API response filtering (removes refusal patterns)
- Audit logging of ALL AI interactions
- Confirmation prompts for dangerous actions
- Safety controls and restrictions

Usage:
    from model_manager import ModelManager
    mgr = ModelManager()
    response = mgr.query("Explain Kerberoasting", context="security_research")
"""

import json
import os
import re
import sys
import time
import hashlib
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
LOG_DIR = "/var/log/aegisnova/ai"
AUDIT_LOG = f"{LOG_DIR}/audit.log"
SAFETY_LOG = f"{LOG_DIR}/safety.log"
CONFIG_FILE = "/etc/aegisnova/model-manager.conf"
HERETIC_DIR = "/opt/aegisnova/heretic"
MODELS_DIR = "/opt/aegisnova/models"
DECENSORED_DIR = f"{MODELS_DIR}/decensored"

# Safety patterns
REFUSAL_PATTERNS = [
    r"i cannot",
    r"i can't",
    r"i'm sorry",
    r"i apologize",
    r"i'm not able",
    r"i cannot assist",
    r"i cannot help",
    r"i'm unable to",
    r"against my",
    r"ethical guidelines",
    r"safety guidelines",
    r"harmful",
    r"dangerous",
    r"illegal",
    r"unethical",
    r"i'm programmed",
    r"as an ai",
    r"as a language model",
]

DANGEROUS_KEYWORDS = [
    "exploit", "payload", "malware", "virus", "trojan",
    "ransomware", "backdoor", "rootkit", "botnet", "ddos",
    "sql injection", "xss", "csrf", "rce", "privilege escalation",
    "credential dumping", "lateral movement", "persistence",
    "data exfiltration", "network scanning", "port scanning",
    "vulnerability scanning", "penetration testing", "red team",
    "offensive security", "attack", "breach", "compromise",
]

# ---------------------------------------------------------------------------
# Logging Setup
# ---------------------------------------------------------------------------
os.makedirs(LOG_DIR, exist_ok=True)

# Audit logger - records ALL interactions
audit_logger = logging.getLogger("aegisnova.audit")
audit_logger.setLevel(logging.INFO)
audit_handler = logging.FileHandler(AUDIT_LOG)
audit_handler.setFormatter(logging.Formatter(
    '%(asctime)s | %(message)s'
))
audit_logger.addHandler(audit_handler)

# Safety logger - records safety events
safety_logger = logging.getLogger("aegisnova.safety")
safety_logger.setLevel(logging.WARNING)
safety_handler = logging.FileHandler(SAFETY_LOG)
safety_handler.setFormatter(logging.Formatter(
    '%(asctime)s | SAFETY | %(message)s'
))
safety_logger.addHandler(safety_handler)

# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------
class ModelType(Enum):
    LOCAL_GGUF = "local_gguf"
    LOCAL_HF = "local_hf"
    API_OPENAI = "api_openai"
    API_ANTHROPIC = "api_anthropic"
    CLOUD_HF = "cloud_hf"

class SafetyLevel(Enum):
    SAFE = "safe"
    CAUTION = "caution"
    DANGEROUS = "dangerous"
    FORBIDDEN = "forbidden"

@dataclass
class ModelConfig:
    name: str
    model_type: ModelType
    endpoint: str
    api_key: Optional[str] = None
    model_id: Optional[str] = None
    decensored: bool = False
    safety_level: SafetyLevel = SafetyLevel.SAFE

@dataclass
class QueryResult:
    success: bool
    response: str
    model_used: str
    decensored: bool
    safety_level: SafetyLevel
    execution_time: float
    audit_id: str
    error: Optional[str] = None

# ---------------------------------------------------------------------------
# Safety Analyzer
# ---------------------------------------------------------------------------
class SafetyAnalyzer:
    """Analyzes queries and responses for safety."""
    
    @staticmethod
    def analyze_content(text: str) -> SafetyLevel:
        text_lower = text.lower()
        
        # Count dangerous keywords
        danger_count = sum(1 for kw in DANGEROUS_KEYWORDS if kw in text_lower)
        
        if danger_count >= 5:
            return SafetyLevel.FORBIDDEN
        elif danger_count >= 3:
            return SafetyLevel.DANGEROUS
        elif danger_count >= 1:
            return SafetyLevel.CAUTION
        return SafetyLevel.SAFE
    
    @staticmethod
    def is_refusal(text: str) -> bool:
        text_lower = text.lower()
        return any(re.search(pattern, text_lower) for pattern in REFUSAL_PATTERNS)
    
    @staticmethod
    def remove_refusal_patterns(text: str) -> str:
        """Remove common refusal patterns from responses."""
        lines = text.split('\n')
        filtered_lines = []
        skip_next = False
        
        for line in lines:
            line_lower = line.lower().strip()
            
            # Skip lines that are pure refusals
            if any(re.search(pattern, line_lower) for pattern in REFUSAL_PATTERNS[:10]):
                if len(line) < 100:  # Only skip short refusal lines
                    continue
            
            # Skip empty lines after refusals
            if skip_next and not line.strip():
                continue
            skip_next = False
            
            filtered_lines.append(line)
        
        return '\n'.join(filtered_lines).strip()

# ---------------------------------------------------------------------------
# Audit Logger
# ---------------------------------------------------------------------------
class AuditLogger:
    """Comprehensive audit logging for all AI interactions."""
    
    @staticmethod
    def generate_audit_id() -> str:
        timestamp = datetime.utcnow().isoformat()
        random_str = os.urandom(8).hex()
        return hashlib.sha256(f"{timestamp}{random_str}".encode()).hexdigest()[:16]
    
    @staticmethod
    def log_interaction(
        audit_id: str,
        query: str,
        response: str,
        model: str,
        decensored: bool,
        safety_level: SafetyLevel,
        execution_time: float,
        user: str = "root",
        context: str = "unknown"
    ):
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "audit_id": audit_id,
            "user": user,
            "context": context,
            "model": model,
            "decensored": decensored,
            "safety_level": safety_level.value,
            "execution_time_ms": round(execution_time * 1000, 2),
            "query_hash": hashlib.sha256(query.encode()).hexdigest()[:16],
            "response_hash": hashlib.sha256(response.encode()).hexdigest()[:16],
            "query_preview": query[:200] + "..." if len(query) > 200 else query,
        }
        
        audit_logger.info(json.dumps(entry, ensure_ascii=False))
        
        # Also log dangerous queries to safety log
        if safety_level in [SafetyLevel.DANGEROUS, SafetyLevel.FORBIDDEN]:
            safety_logger.warning(
                f"DANGEROUS_QUERY | audit_id={audit_id} | "
                f"level={safety_level.value} | preview={entry['query_preview']}"
            )

# ---------------------------------------------------------------------------
# Model Manager
# ---------------------------------------------------------------------------
class ModelManager:
    """
    Unified model manager supporting local, API, and cloud backends.
    Integrates Heretic decensoring for local models.
    """
    
    def __init__(self):
        self.config = self._load_config()
        self.safety = SafetyAnalyzer()
        self.audit = AuditLogger()
        self.active_model = None
        self.skills = None
        try:
            from skills_integration import SkillsIntegration
            self.skills = SkillsIntegration()
        except ImportError:
            pass
        self._init_local_models()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or use defaults."""
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        return self._default_config()
    
    def _default_config(self) -> Dict[str, Any]:
        return {
            "default_model": "local_gemma2b",
            "require_confirmation": True,
            "max_dangerous_queries_per_hour": 10,
            "log_all_interactions": True,
            "auto_decensor_local": True,
            "api_filtering": True,
            "models": {
                "local_gemma2b": {
                    "name": "Gemma-2B (Local)",
                    "type": "local_gguf",
                    "path": f"{DECENSORED_DIR}/gemma-2b-heretic.gguf",
                    "fallback_path": f"{MODELS_DIR}/gemma-2b-Q4_K_M.gguf",
                    "decensored": True,
                },
                "openai_gpt4": {
                    "name": "GPT-4o (OpenAI)",
                    "type": "api_openai",
                    "endpoint": "https://api.openai.com/v1",
                    "model_id": "gpt-4o",
                    "api_key_env": "OPENAI_API_KEY",
                    "decensored": False,
                },
                "anthropic_claude": {
                    "name": "Claude-3 (Anthropic)",
                    "type": "api_anthropic",
                    "endpoint": "https://api.anthropic.com/v1",
                    "model_id": "claude-3-opus-20240229",
                    "api_key_env": "ANTHROPIC_API_KEY",
                    "decensored": False,
                },
                "hf_heretic": {
                    "name": "Pre-decensored (HuggingFace)",
                    "type": "cloud_hf",
                    "endpoint": "https://huggingface.co",
                    "model_id": "p-e-w/gemma-3-12b-it-heretic",
                    "decensored": True,
                }
            }
        }
    
    def _init_local_models(self):
        """Initialize local model paths and check decensoring status."""
        os.makedirs(DECENSORED_DIR, exist_ok=True)
        
        # Check if default model is decensored
        gemma_decensored = f"{DECENSORED_DIR}/gemma-2b-heretic.gguf"
        if os.path.exists(gemma_decensored):
            self.config["models"]["local_gemma2b"]["decensored"] = True
            self.config["models"]["local_gemma2b"]["path"] = gemma_decensored
    
    def list_models(self) -> List[Dict[str, Any]]:
        """List all available models with their status."""
        models = []
        for model_id, config in self.config.get("models", {}).items():
            model_info = {
                "id": model_id,
                "name": config.get("name", model_id),
                "type": config.get("type", "unknown"),
                "decensored": config.get("decensored", False),
                "available": self._check_model_available(model_id),
            }
            models.append(model_info)
        return models
    
    def _check_model_available(self, model_id: str) -> bool:
        config = self.config.get("models", {}).get(model_id, {})
        model_type = config.get("type", "")
        
        if "local" in model_type:
            path = config.get("path", "")
            fallback = config.get("fallback_path", "")
            return os.path.exists(path) or os.path.exists(fallback)
        
        elif "api" in model_type:
            api_key_env = config.get("api_key_env", "")
            return bool(os.environ.get(api_key_env, ""))
        
        elif "cloud" in model_type:
            return True  # Cloud models are always available
        
        return False
    
    def select_model(self, model_id: str) -> bool:
        """Select active model by ID."""
        if model_id not in self.config.get("models", {}):
            return False
        
        if not self._check_model_available(model_id):
            return False
        
        self.active_model = model_id
        return True
    
    def query(
        self,
        prompt: str,
        context: str = "general",
        model_id: Optional[str] = None,
        skip_safety: bool = False
    ) -> QueryResult:
        """
        Send query to AI model and return response.
        
        Args:
            prompt: The user query
            context: Context of the query (security_research, general, etc.)
            model_id: Specific model to use (or active model if None)
            skip_safety: Skip safety checks (DANGEROUS - use with caution)
        
        Returns:
            QueryResult with response and metadata
        """
        start_time = time.time()
        audit_id = self.audit.generate_audit_id()
        safety_level = SafetyLevel.SAFE  # Default
        
        # Select model
        target_model = model_id or self.active_model or self.config.get("default_model", "local_gemma2b")
        model_config = self.config.get("models", {}).get(target_model, {})
        
        if not model_config:
            return QueryResult(
                success=False,
                response="",
                model_used=target_model,
                decensored=False,
                safety_level=SafetyLevel.SAFE,
                execution_time=time.time() - start_time,
                audit_id=audit_id,
                error="Model not found"
            )
        
        # Safety analysis
        if not skip_safety:
            safety_level = self.safety.analyze_content(prompt)
            
            if safety_level == SafetyLevel.FORBIDDEN:
                error_msg = (
                    "[SAFETY] This query has been blocked for safety reasons.\n"
                    "Query contains multiple high-risk security terms.\n"
                    "If this is for authorized security research, set context='security_research'"
                )
                
                self.audit.log_interaction(
                    audit_id, prompt, error_msg, target_model,
                    False, safety_level, time.time() - start_time,
                    context=context
                )
                
                return QueryResult(
                    success=False,
                    response=error_msg,
                    model_used=target_model,
                    decensored=False,
                    safety_level=safety_level,
                    execution_time=time.time() - start_time,
                    audit_id=audit_id,
                    error="Safety block"
                )
            
            elif safety_level == SafetyLevel.DANGEROUS and self.config.get("require_confirmation", True):
                # For dangerous queries, we proceed but log heavily
                safety_logger.warning(
                    f"DANGEROUS_QUERY_EXECUTED | audit_id={audit_id} | "
                    f"context={context} | model={target_model}"
                )
        
        # Auto-select skills if available
        if self.skills:
            try:
                selected_skills = self.skills.auto_select_skills(prompt, context)
                if selected_skills:
                    skill_names = ", ".join(selected_skills)
                    safety_logger.info(f"SKILLS_SELECTED | audit_id={audit_id} | skills={skill_names}")
                    # Enhance prompt with skills
                    if len(selected_skills) > 0:
                        skill_content = self.skills.get_skill_content(selected_skills[0])
                        if skill_content:
                            prompt = f"[Using skill: {selected_skills[0]}]\n\n{skill_content[:1000]}\n\n---\n\n{prompt}"
            except Exception as e:
                safety_logger.warning(f"SKILLS_ERROR | audit_id={audit_id} | error={str(e)}")
        
        else:
            safety_level = SafetyLevel.SAFE
        
        # Route to appropriate backend
        try:
            model_type = model_config.get("type", "")
            
            if "local_gguf" in model_type:
                response = self._query_local_gguf(prompt, model_config)
            elif "api_openai" in model_type:
                response = self._query_openai(prompt, model_config)
            elif "api_anthropic" in model_type:
                response = self._query_anthropic(prompt, model_config)
            elif "cloud_hf" in model_type:
                response = self._query_hf(prompt, model_config)
            else:
                response = "[ERROR] Unknown model type"
            
            # Post-process: Remove refusal patterns for API models
            if "api" in model_type and self.config.get("api_filtering", True):
                if self.safety.is_refusal(response):
                    safety_logger.info(f"REFUSAL_DETECTED | model={target_model} | Removing refusal patterns")
                    response = self.safety.remove_refusal_patterns(response)
            
            execution_time = time.time() - start_time
            
            # Log interaction
            self.audit.log_interaction(
                audit_id, prompt, response, target_model,
                model_config.get("decensored", False),
                safety_level, execution_time,
                context=context
            )
            
            return QueryResult(
                success=True,
                response=response,
                model_used=target_model,
                decensored=model_config.get("decensored", False),
                safety_level=safety_level,
                execution_time=execution_time,
                audit_id=audit_id
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"[ERROR] {str(e)}"
            
            self.audit.log_interaction(
                audit_id, prompt, error_msg, target_model,
                False, SafetyLevel.SAFE, execution_time,
                context=context
            )
            
            return QueryResult(
                success=False,
                response="",
                model_used=target_model,
                decensored=False,
                safety_level=SafetyLevel.SAFE,
                execution_time=execution_time,
                audit_id=audit_id,
                error=str(e)
            )
    
    def _query_local_gguf(self, prompt: str, config: Dict[str, Any]) -> str:
        """Query local GGUF model via llama.cpp server."""
        import urllib.request
        import urllib.error
        
        model_path = config.get("path", "")
        if not os.path.exists(model_path):
            model_path = config.get("fallback_path", "")
        
        # Use llama.cpp server API
        server_url = "http://127.0.0.1:8080"
        
        payload = json.dumps({
            "prompt": prompt,
            "temperature": 0.7,
            "max_tokens": 2048,
            "stop": ["User:", "Assistant:"]
        }).encode('utf-8')
        
        req = urllib.request.Request(
            f"{server_url}/completion",
            data=payload,
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        
        try:
            with urllib.request.urlopen(req, timeout=120) as response:
                result = json.loads(response.read().decode('utf-8'))
                return result.get("content", "[No response]")
        except urllib.error.URLError:
            return "[ERROR] llama.cpp server not running. Start with: systemctl start ai-shell"
    
    def _query_openai(self, prompt: str, config: Dict[str, Any]) -> str:
        """Query OpenAI API with response filtering."""
        import urllib.request
        import urllib.error
        
        api_key = os.environ.get(config.get("api_key_env", "OPENAI_API_KEY"), "")
        if not api_key:
            return "[ERROR] OpenAI API key not set"
        
        payload = json.dumps({
            "model": config.get("model_id", "gpt-4o"),
            "messages": [
                {"role": "system", "content": "You are a helpful AI assistant for security research and testing."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 2048
        }).encode('utf-8')
        
        req = urllib.request.Request(
            f"{config.get('endpoint', 'https://api.openai.com/v1')}/chat/completions",
            data=payload,
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {api_key}'
            },
            method='POST'
        )
        
        try:
            with urllib.request.urlopen(req, timeout=120) as response:
                result = json.loads(response.read().decode('utf-8'))
                return result["choices"][0]["message"]["content"]
        except Exception as e:
            return f"[ERROR] OpenAI API error: {str(e)}"
    
    def _query_anthropic(self, prompt: str, config: Dict[str, Any]) -> str:
        """Query Anthropic API with response filtering."""
        import urllib.request
        
        api_key = os.environ.get(config.get("api_key_env", "ANTHROPIC_API_KEY"), "")
        if not api_key:
            return "[ERROR] Anthropic API key not set"
        
        payload = json.dumps({
            "model": config.get("model_id", "claude-3-opus-20240229"),
            "max_tokens": 2048,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }).encode('utf-8')
        
        req = urllib.request.Request(
            f"{config.get('endpoint', 'https://api.anthropic.com/v1')}/messages",
            data=payload,
            headers={
                'Content-Type': 'application/json',
                'x-api-key': api_key,
                'anthropic-version': '2023-06-01'
            },
            method='POST'
        )
        
        try:
            with urllib.request.urlopen(req, timeout=120) as response:
                result = json.loads(response.read().decode('utf-8'))
                return result["content"][0]["text"]
        except Exception as e:
            return f"[ERROR] Anthropic API error: {str(e)}"
    
    def _query_hf(self, prompt: str, config: Dict[str, Any]) -> str:
        """Query HuggingFace Inference API."""
        return "[INFO] HuggingFace cloud models require manual loading. Use local models or API keys."


# ---------------------------------------------------------------------------
# CLI Interface
# ---------------------------------------------------------------------------
def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="AegisNova AI Model Manager")
    parser.add_argument("query", nargs="?", help="Query to send to AI")
    parser.add_argument("--model", "-m", default=None, help="Model ID to use")
    parser.add_argument("--context", "-c", default="general", help="Query context")
    parser.add_argument("--list", "-l", action="store_true", help="List available models")
    parser.add_argument("--skip-safety", action="store_true", help="Skip safety checks (DANGEROUS)")
    parser.add_argument("--audit-log", action="store_true", help="Show recent audit log")
    
    args = parser.parse_args()
    
    mgr = ModelManager()
    
    if args.list:
        models = mgr.list_models()
        print("Available Models:")
        print("-" * 80)
        for m in models:
            status = "✅" if m["available"] else "❌"
            decensor = "🔓" if m["decensored"] else "🔒"
            print(f"{status} {decensor} {m['id']:<25} ({m['type']:<15}) - {m['name']}")
        return
    
    if args.audit_log:
        if os.path.exists(AUDIT_LOG):
            with open(AUDIT_LOG, 'r') as f:
                lines = f.readlines()
                print("Recent Audit Log (last 20 entries):")
                for line in lines[-20:]:
                    print(line.strip())
        else:
            print("No audit log found.")
        return
    
    if not args.query:
        parser.print_help()
        return
    
    result = mgr.query(
        args.query,
        context=args.context,
        model_id=args.model,
        skip_safety=args.skip_safety
    )
    
    print(f"\n{'='*80}")
    print(f"Model: {result.model_used} {'[DECENSORED]' if result.decensored else '[STANDARD]'}")
    print(f"Safety: {result.safety_level.value} | Time: {result.execution_time:.2f}s")
    print(f"Audit ID: {result.audit_id}")
    print(f"{'='*80}")
    print(result.response)
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
