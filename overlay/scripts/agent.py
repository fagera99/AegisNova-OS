#!/usr/bin/env python3
"""
AegisNova OS — LangChain Security Agent (Minimal Example)
===========================================================
Demonstrates a LangChain tool-use loop that orchestrates security tools
via an LLM. Usable standalone or embedded in the eBPF sensor / Jupyter.

Usage:
    python3 agent.py "Scan 192.168.1.0/24 for open ports"
    python3 agent.py "Generate Sigma rule for suspicious powershell"
"""

import json
import os
import subprocess
import sys
from typing import Optional

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
LLM_ENDPOINT = os.getenv("LLM_ENDPOINT", "http://127.0.0.1:8080/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "local")

# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------
def run_nmap(target: str) -> str:
    """Run a quick nmap scan against a target."""
    try:
        result = subprocess.run(
            ["nmap", "-sV", "--top-ports", "100", "-T4", target],
            capture_output=True, text=True, timeout=120,
        )
        return result.stdout[:2000]
    except Exception as e:
        return f"nmap error: {e}"


def query_exploitdb(term: str) -> str:
    """Search ExploitDB for a vulnerability."""
    try:
        result = subprocess.run(
            ["searchsploit", "--json", term],
            capture_output=True, text=True, timeout=30,
        )
        return result.stdout[:2000]
    except Exception as e:
        return f"searchsploit error: {e}"


def generate_sigma_rule(description: str) -> str:
    """Generate a Sigma detection rule from a description."""
    template = {
        "title": f"AI-Generated: {description[:60]}",
        "status": "experimental",
        "description": description,
        "logsource": {"category": "process_creation", "product": "linux"},
        "detection": {
            "selection": {"CommandLine|contains": ["suspicious_pattern"]},
            "condition": "selection",
        },
        "level": "medium",
        "tags": ["attack.execution"],
    }
    return json.dumps(template, indent=2)


def check_cve(cve_id: str) -> str:
    """Look up a CVE via local data or NVD."""
    try:
        import requests
        resp = requests.get(
            f"https://services.nvd.nist.gov/rest/json/cves/2.0?cveId={cve_id}",
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            vulns = data.get("vulnerabilities", [])
            if vulns:
                desc = vulns[0]["cve"]["descriptions"][0]["value"]
                return f"{cve_id}: {desc[:500]}"
        return f"No data found for {cve_id}"
    except Exception as e:
        return f"CVE lookup error: {e}"


def run_lynis_audit() -> str:
    """Run a quick Lynis system audit."""
    try:
        result = subprocess.run(
            ["lynis", "audit", "system", "--quick", "--no-colors"],
            capture_output=True, text=True, timeout=120,
        )
        # Extract just the warnings and suggestions
        lines = result.stdout.split("\n")
        important = [l for l in lines if "Warning" in l or "Suggestion" in l]
        return "\n".join(important[:20]) if important else "No warnings found."
    except Exception as e:
        return f"lynis error: {e}"


# ---------------------------------------------------------------------------
# Tool registry
# ---------------------------------------------------------------------------
TOOLS = {
    "nmap_scan": {
        "func": run_nmap,
        "desc": "Scan a target IP/network for open ports and services.",
    },
    "search_exploits": {
        "func": query_exploitdb,
        "desc": "Search ExploitDB for known exploits matching a term.",
    },
    "generate_sigma": {
        "func": generate_sigma_rule,
        "desc": "Generate a Sigma detection rule from a description.",
    },
    "check_cve": {
        "func": check_cve,
        "desc": "Look up a CVE ID to get vulnerability details.",
    },
    "lynis_audit": {
        "func": run_lynis_audit,
        "desc": "Run a quick system hardening audit with Lynis.",
    },
}


# ---------------------------------------------------------------------------
# Simple LLM tool-use loop (no LangChain dependency)
# ---------------------------------------------------------------------------
def call_llm(prompt: str) -> str:
    """Call the local LLM endpoint."""
    try:
        import requests
        resp = requests.post(
            LLM_ENDPOINT.rstrip("/").replace("/v1", "") + "/completion",
            json={"prompt": prompt, "n_predict": 500, "temperature": 0.2, "stop": ["\n\n"]},
            timeout=30,
        )
        if resp.status_code == 200:
            return resp.json().get("content", "")
    except Exception as e:
        return f"LLM error: {e}"
    return ""


def agent_loop(user_query: str, max_iterations: int = 5) -> str:
    """
    ReAct-style tool-use loop:
      Thought → Action → Observation → ... → Final Answer
    """
    tool_descriptions = "\n".join(
        f"  - {name}: {info['desc']}" for name, info in TOOLS.items()
    )

    system_prompt = f"""You are a security analyst AI agent with access to these tools:
{tool_descriptions}

To use a tool, respond EXACTLY in this format:
Action: <tool_name>
Input: <tool_input>

When you have enough information, respond with:
Final Answer: <your answer>

User request: {user_query}
"""

    conversation = system_prompt
    print(f"\n{'═' * 60}")
    print(f"  AegisNova Security Agent")
    print(f"  Query: {user_query}")
    print(f"{'═' * 60}\n")

    for i in range(max_iterations):
        response = call_llm(conversation)
        print(f"[Agent Step {i+1}] {response[:200]}")

        if "Final Answer:" in response:
            answer = response.split("Final Answer:")[-1].strip()
            print(f"\n✅ Final Answer: {answer}")
            return answer

        if "Action:" in response and "Input:" in response:
            action_line = [l for l in response.split("\n") if l.startswith("Action:")]
            input_line = [l for l in response.split("\n") if l.startswith("Input:")]

            if action_line and input_line:
                tool_name = action_line[0].replace("Action:", "").strip()
                tool_input = input_line[0].replace("Input:", "").strip()

                if tool_name in TOOLS:
                    print(f"  🔧 Executing: {tool_name}({tool_input})")
                    observation = TOOLS[tool_name]["func"](tool_input)
                    conversation += f"\n{response}\nObservation: {observation}\n"
                    print(f"  📋 Observation: {observation[:200]}...")
                else:
                    conversation += f"\nObservation: Tool '{tool_name}' not found.\n"
        else:
            # No action, treat as final
            return response

    return "Agent reached max iterations without a final answer."


# ---------------------------------------------------------------------------
# LangChain agent (when langchain is available)
# ---------------------------------------------------------------------------
def create_langchain_agent(query: str) -> Optional[str]:
    """Use LangChain if available for richer agent capabilities."""
    try:
        from langchain.agents import initialize_agent, AgentType
        from langchain.tools import Tool
        from langchain_openai import ChatOpenAI

        lc_tools = [
            Tool(name=name, func=info["func"], description=info["desc"])
            for name, info in TOOLS.items()
        ]

        llm = ChatOpenAI(
            base_url=LLM_ENDPOINT,
            api_key="not-needed",
            model=LLM_MODEL,
            temperature=0.1,
        )

        agent = initialize_agent(
            lc_tools, llm,
            agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
            verbose=True,
            max_iterations=5,
        )

        return agent.run(query)
    except ImportError:
        return None


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: agent.py <query>")
        print('Example: agent.py "Scan 10.0.0.0/24 for web servers"')
        sys.exit(1)

    query = " ".join(sys.argv[1:])

    # Try LangChain first, fall back to simple loop
    result = create_langchain_agent(query)
    if result is None:
        result = agent_loop(query)

    print(f"\n{'─' * 60}")
    print(f"Result: {result}")
