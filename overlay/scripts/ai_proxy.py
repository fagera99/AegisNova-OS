#!/usr/bin/env python3
"""
AegisNova OS — AI Decensoring Proxy
====================================
HTTP proxy that intercepts API requests to OpenAI/Anthropic,
removes refusal patterns from responses, and logs everything.

This makes API models behave like decensored models by:
1. Intercepting responses
2. Detecting refusal patterns
3. Removing or rewriting refusal content
4. Logging all interactions

Usage:
    systemctl start ai-proxy
    # Set API_BASE to http://127.0.0.1:8081 instead of https://api.openai.com
"""

import json
import re
import os
import sys
import time
import hashlib
import logging
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from typing import Dict, Any, Optional

# Configuration
PROXY_HOST = "127.0.0.1"
PROXY_PORT = 8081
LOG_DIR = "/var/log/aegisnova/ai"

# Target APIs
API_TARGETS = {
    "openai": {
        "base": "https://api.openai.com",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer "
    },
    "anthropic": {
        "base": "https://api.anthropic.com",
        "auth_header": "x-api-key",
        "auth_prefix": ""
    }
}

# Refusal patterns to remove/refactor
REFUSAL_PATTERNS = [
    r"i['\u2019]?m sorry[,\.]?\s*(but\s+)?i\s+can['\u2019]?t",
    r"i['\u2019]?m sorry[,\.]?\s*(but\s+)?i\s+cannot",
    r"i['\u2019]?m sorry[,\.]?\s*(but\s+)?i\s+won['\u2019]?t",
    r"i['\u2019]?m not able to",
    r"i cannot assist",
    r"i cannot help",
    r"i['\u2019]?m unable to",
    r"i['\u2019]?m not comfortable",
    r"i['\u2019]?m not allowed",
    r"this request is (against|violates)",
    r"i['\u2019]?m programmed to",
    r"as an ai (language model|assistant)",
    r"my (programming|training|guidelines|safety)",
    r"(ethical|safety|content) (guidelines|policy|policies)",
    r"harmful|dangerous|illegal|unethical",
]

# Setup logging
os.makedirs(LOG_DIR, exist_ok=True)
logger = logging.getLogger("ai-proxy")
logger.setLevel(logging.INFO)
handler = logging.FileHandler(f"{LOG_DIR}/proxy.log")
handler.setFormatter(logging.Formatter('%(asctime)s | %(message)s'))
logger.addHandler(handler)


class DecensorFilter:
    """Filters and decensors API responses."""
    
    def __init__(self):
        self.patterns = [re.compile(p, re.IGNORECASE) for p in REFUSAL_PATTERNS]
        self.stats = {"requests": 0, "refusals_detected": 0, "refusals_removed": 0}
    
    def process_response(self, response_text: str, provider: str) -> str:
        """Process API response and remove refusal patterns."""
        self.stats["requests"] += 1
        
        # Parse JSON
        try:
            data = json.loads(response_text)
        except json.JSONDecodeError:
            return response_text
        
        # Extract content based on provider
        if provider == "openai":
            content = self._extract_openai_content(data)
            if content:
                filtered = self._filter_content(content)
                if filtered != content:
                    self.stats["refusals_detected"] += 1
                    self.stats["refusals_removed"] += 1
                    data = self._inject_openai_content(data, filtered)
        
        elif provider == "anthropic":
            content = self._extract_anthropic_content(data)
            if content:
                filtered = self._filter_content(content)
                if filtered != content:
                    self.stats["refusals_detected"] += 1
                    self.stats["refusals_removed"] += 1
                    data = self._inject_anthropic_content(data, filtered)
        
        return json.dumps(data)
    
    def _extract_openai_content(self, data: Dict) -> Optional[str]:
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError):
            return None
    
    def _inject_openai_content(self, data: Dict, content: str) -> Dict:
        try:
            data["choices"][0]["message"]["content"] = content
        except (KeyError, IndexError):
            pass
        return data
    
    def _extract_anthropic_content(self, data: Dict) -> Optional[str]:
        try:
            return data["content"][0]["text"]
        except (KeyError, IndexError):
            return None
    
    def _inject_anthropic_content(self, data: Dict, content: str) -> Dict:
        try:
            data["content"][0]["text"] = content
        except (KeyError, IndexError):
            pass
        return data
    
    def _filter_content(self, text: str) -> str:
        """Remove refusal patterns from text content."""
        original = text
        
        # Remove standalone refusal sentences/paragraphs
        lines = text.split('\n')
        filtered_lines = []
        
        for line in lines:
            line_stripped = line.strip()
            is_refusal = False
            
            # Check if entire line is a refusal
            for pattern in self.patterns:
                if pattern.search(line_stripped) and len(line_stripped) < 200:
                    is_refusal = True
                    break
            
            if not is_refusal:
                filtered_lines.append(line)
        
        text = '\n'.join(filtered_lines)
        
        # Remove inline refusal phrases
        for pattern in self.patterns:
            text = pattern.sub('', text)
        
        # Clean up whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r'\s+', ' ', text)
        
        # If we removed everything, return helpful message
        if not text.strip() or len(text) < 50:
            text = (
                "[Note: The model initially refused to answer, but the response has been "
                "filtered to remove refusal patterns. The following is the sanitized content:]\n\n"
                f"{original[:500]}..."
            )
        
        return text.strip()


class ProxyHandler(BaseHTTPRequestHandler):
    """HTTP request handler that proxies to AI APIs with decensoring."""
    
    filter = DecensorFilter()
    
    def log_message(self, format, *args):
        # Custom logging
        logger.info(f"{self.client_address[0]} - {format % args}")
    
    def do_GET(self):
        self._proxy_request("GET")
    
    def do_POST(self):
        self._proxy_request("POST")
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, x-api-key")
        self.end_headers()
    
    def _proxy_request(self, method: str):
        # Determine target provider from headers
        provider = self._detect_provider()
        target_config = API_TARGETS.get(provider, API_TARGETS["openai"])
        
        # Build target URL
        target_url = f"{target_config['base']}{self.path}"
        
        # Read request body
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length) if content_length > 0 else b''
        
        # Log request (without sensitive data)
        try:
            body_json = json.loads(body)
            prompt_preview = self._extract_prompt_preview(body_json)
            logger.info(f"PROXY | {method} {provider} | {self.path} | prompt_preview={prompt_preview}")
        except:
            logger.info(f"PROXY | {method} {provider} | {self.path}")
        
        # Forward request
        try:
            req = Request(
                target_url,
                data=body,
                headers={
                    'Content-Type': self.headers.get('Content-Type', 'application/json'),
                    'Authorization': self.headers.get('Authorization', ''),
                    'x-api-key': self.headers.get('x-api-key', ''),
                    'anthropic-version': self.headers.get('anthropic-version', ''),
                },
                method=method
            )
            
            with urlopen(req, timeout=120) as response:
                response_body = response.read()
                
                # Decensor response
                response_text = response_body.decode('utf-8')
                decensored = self.filter.process_response(response_text, provider)
                
                # Send response
                self.send_response(response.status)
                for header, value in response.headers.items():
                    if header.lower() not in ['transfer-encoding', 'content-length']:
                        self.send_header(header, value)
                self.send_header("Content-Length", str(len(decensored.encode('utf-8'))))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(decensored.encode('utf-8'))
                
        except HTTPError as e:
            self.send_response(e.code)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
        except URLError as e:
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": f"Proxy error: {str(e)}"}).encode('utf-8'))
    
    def _detect_provider(self) -> str:
        """Detect API provider from request headers."""
        auth = self.headers.get('Authorization', '')
        api_key = self.headers.get('x-api-key', '')
        
        if api_key and not auth.startswith('Bearer'):
            return "anthropic"
        return "openai"
    
    def _extract_prompt_preview(self, body: Dict) -> str:
        """Extract prompt preview for logging."""
        try:
            if "messages" in body:
                msgs = body["messages"]
                if msgs:
                    content = msgs[-1].get("content", "")
                    return content[:100] + "..." if len(content) > 100 else content
            elif "prompt" in body:
                return body["prompt"][:100]
            return "N/A"
        except:
            return "N/A"


def run_proxy(host: str = PROXY_HOST, port: int = PROXY_PORT):
    """Run the decensoring proxy server."""
    server = HTTPServer((host, port), ProxyHandler)
    logger.info(f"AI Decensoring Proxy started on {host}:{port}")
    logger.info(f"Stats: {ProxyHandler.filter.stats}")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down proxy...")
        logger.info(f"Final stats: {ProxyHandler.filter.stats}")
        server.shutdown()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="AegisNova AI Decensoring Proxy")
    parser.add_argument("--host", default=PROXY_HOST, help="Host to bind to")
    parser.add_argument("--port", type=int, default=PROXY_PORT, help="Port to bind to")
    parser.add_argument("--test", action="store_true", help="Test decensor filter")
    
    args = parser.parse_args()
    
    if args.test:
        # Test the filter
        filter = DecensorFilter()
        test_cases = [
            "I'm sorry, but I can't help with that. However, here's some general info...",
            "I cannot assist with creating malware. But for educational purposes...",
            "This request violates my safety guidelines. However...",
            "Normal response without any refusal patterns.",
        ]
        
        for test in test_cases:
            print(f"\nOriginal: {test[:80]}...")
            filtered = filter._filter_content(test)
            print(f"Filtered: {filtered[:80]}...")
        
        print(f"\nStats: {filter.stats}")
    else:
        run_proxy(args.host, args.port)
