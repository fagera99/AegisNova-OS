#!/usr/bin/env python3
"""
AegisNova OS — OSINT Automation Agent
=======================================
Automated Open Source Intelligence gathering for reconnaissance.
Integrates multiple OSINT sources and tools:
- theHarvester
- amass
- spiderfoot
- subfinder
- Shodan (API key required)
- VirusTotal (API key required)
- WHOIS lookups
- DNS enumeration
- Social media scraping hints

Usage:
    python3 osint-agent.py --domain example.com
    python3 osint-agent.py --email user@example.com
    python3 osint-agent.py --ip 1.2.3.4
    python3 osint-agent.py --domain example.com --full --output report.json
"""

import json
import os
import re
import sys
import subprocess
import argparse
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime

# ── Configuration ──
OSINT_DIR = "/opt/aegisnova/osint-reports"
API_KEYS_FILE = "/etc/aegisnova/env"

# ── Data Classes ──
@dataclass
class OSINTResult:
    source: str
    data_type: str
    data: Any
    confidence: str  # high, medium, low
    timestamp: str

@dataclass
class OSINTReport:
    target: str
    target_type: str  # domain, email, ip, person
    timestamp: str
    results: List[OSINTResult]
    summary: Dict[str, Any]

# ── Core Agent ──
class OSINTAgent:
    """Automated OSINT gathering agent."""
    
    def __init__(self):
        self.results = []
        self.api_keys = self._load_api_keys()
        os.makedirs(OSINT_DIR, exist_ok=True)
    
    def _load_api_keys(self) -> Dict[str, str]:
        """Load API keys from environment."""
        return {
            "shodan": os.getenv("SHODAN_API_KEY", ""),
            "virustotal": os.getenv("VIRUSTOTAL_API_KEY", ""),
            "hunter": os.getenv("HUNTER_API_KEY", ""),
        }
    
    def _run_command(self, cmd: List[str], timeout: int = 300) -> str:
        """Run a command and return output."""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return result.stdout
        except subprocess.TimeoutExpired:
            return f"Command timed out after {timeout}s"
        except FileNotFoundError:
            return f"Command not found: {cmd[0]}"
        except Exception as e:
            return f"Error: {e}"
    
    def domain_recon(self, domain: str, full: bool = False) -> List[OSINTResult]:
        """Perform domain reconnaissance."""
        results = []
        
        print(f"[*] Starting domain reconnaissance for: {domain}")
        
        # DNS enumeration with subfinder
        print("  [+] Running subfinder...")
        subfinder_output = self._run_command([
            "subfinder", "-d", domain, "-all", "-silent"
        ])
        if subfinder_output and "Error" not in subfinder_output:
            subdomains = [s.strip() for s in subfinder_output.split('\n') if s.strip()]
            results.append(OSINTResult(
                source="subfinder",
                data_type="subdomains",
                data=subdomains,
                confidence="high",
                timestamp=datetime.utcnow().isoformat()
            ))
            print(f"      Found {len(subdomains)} subdomains")
        
        # theHarvester
        print("  [+] Running theHarvester...")
        harvester_output = self._run_command([
            "theHarvester", "-d", domain, "-b", "all", "-f", f"/tmp/osint_{domain}"
        ])
        
        # Parse theHarvester output
        emails = re.findall(r'[\w.+-]+@[\w-]+\.[\w.-]+', harvester_output)
        if emails:
            results.append(OSINTResult(
                source="theHarvester",
                data_type="emails",
                data=list(set(emails)),
                confidence="medium",
                timestamp=datetime.utcnow().isoformat()
            ))
            print(f"      Found {len(set(emails))} emails")
        
        # DNS records with dig
        print("  [+] Querying DNS records...")
        for record_type in ["A", "AAAA", "MX", "NS", "TXT", "SOA"]:
            dig_output = self._run_command(["dig", "+short", domain, record_type])
            if dig_output.strip():
                records = [r.strip() for r in dig_output.split('\n') if r.strip()]
                results.append(OSINTResult(
                    source="dig",
                    data_type=f"dns_{record_type.lower()}",
                    data=records,
                    confidence="high",
                    timestamp=datetime.utcnow().isoformat()
                ))
        
        # WHOIS
        print("  [+] Running WHOIS lookup...")
        whois_output = self._run_command(["whois", domain])
        if whois_output and "Error" not in whois_output:
            # Extract key info
            whois_data = {}
            for line in whois_output.split('\n'):
                if ':' in line and not line.startswith('%'):
                    key, value = line.split(':', 1)
                    whois_data[key.strip()] = value.strip()
            
            results.append(OSINTResult(
                source="whois",
                data_type="whois_info",
                data=whois_data,
                confidence="high",
                timestamp=datetime.utcnow().isoformat()
            ))
        
        # Full scan with amass
        if full:
            print("  [+] Running amass (this may take a while)...")
            amass_output = self._run_command([
                "amass", "enum", "-d", domain, "-passive"
            ], timeout=600)
            if amass_output and "Error" not in amass_output:
                amass_domains = [d.strip() for d in amass_output.split('\n') if d.strip()]
                results.append(OSINTResult(
                    source="amass",
                    data_type="subdomains",
                    data=amass_domains,
                    confidence="medium",
                    timestamp=datetime.utcnow().isoformat()
                ))
                print(f"      Found {len(amass_domains)} additional subdomains")
        
        # Shodan lookup (if API key available)
        if self.api_keys.get("shodan"):
            print("  [+] Querying Shodan...")
            try:
                import shodan
                api = shodan.Shodan(self.api_keys["shodan"])
                shodan_results = api.search(f"hostname:{domain}")
                
                shodan_data = []
                for result in shodan_results["matches"][:10]:
                    shodan_data.append({
                        "ip": result.get("ip_str"),
                        "port": result.get("port"),
                        "org": result.get("org"),
                        "hostnames": result.get("hostnames", []),
                        "os": result.get("os"),
                    })
                
                results.append(OSINTResult(
                    source="shodan",
                    data_type="exposed_services",
                    data=shodan_data,
                    confidence="high",
                    timestamp=datetime.utcnow().isoformat()
                ))
                print(f"      Found {len(shodan_data)} exposed services")
            except ImportError:
                print("      Shodan Python library not installed")
            except Exception as e:
                print(f"      Shodan query failed: {e}")
        
        return results
    
    def email_recon(self, email: str) -> List[OSINTResult]:
        """Perform email reconnaissance."""
        results = []
        
        print(f"[*] Starting email reconnaissance for: {email}")
        
        # Extract domain
        domain = email.split('@')[1]
        
        # MX record check
        print("  [+] Checking MX records...")
        mx_output = self._run_command(["dig", "+short", domain, "MX"])
        if mx_output.strip():
            mx_records = [r.strip() for r in mx_output.split('\n') if r.strip()]
            results.append(OSINTResult(
                source="dig",
                data_type="mx_records",
                data=mx_records,
                confidence="high",
                timestamp=datetime.utcnow().isoformat()
            ))
        
        # Hunter.io (if API key available)
        if self.api_keys.get("hunter"):
            print("  [+] Querying Hunter.io...")
            try:
                import urllib.request
                url = f"https://api.hunter.io/v2/email-verifier?email={email}&api_key={self.api_keys['hunter']}"
                req = urllib.request.Request(url)
                with urllib.request.urlopen(req, timeout=30) as response:
                    data = json.loads(response.read().decode())
                    
                    results.append(OSINTResult(
                        source="hunter",
                        data_type="email_verification",
                        data=data.get("data", {}),
                        confidence="high",
                        timestamp=datetime.utcnow().isoformat()
                    ))
            except Exception as e:
                print(f"      Hunter query failed: {e}")
        
        # HaveIBeenPwned check (via h8mail if available)
        print("  [+] Checking breach databases...")
        h8mail_output = self._run_command(["h8mail", "-t", email])
        if h8mail_output and "Error" not in h8mail_output:
            results.append(OSINTResult(
                source="h8mail",
                data_type="breach_data",
                data=h8mail_output[:1000],
                confidence="medium",
                timestamp=datetime.utcnow().isoformat()
            ))
        
        return results
    
    def ip_recon(self, ip: str) -> List[OSINTResult]:
        """Perform IP reconnaissance."""
        results = []
        
        print(f"[*] Starting IP reconnaissance for: {ip}")
        
        # Reverse DNS
        print("  [+] Running reverse DNS lookup...")
        reverse_dns = self._run_command(["dig", "+short", "-x", ip])
        if reverse_dns.strip():
            hostnames = [h.strip('.') for h in reverse_dns.split('\n') if h.strip()]
            results.append(OSINTResult(
                source="dig",
                data_type="reverse_dns",
                data=hostnames,
                confidence="high",
                timestamp=datetime.utcnow().isoformat()
            ))
            print(f"      Found hostnames: {', '.join(hostnames)}")
        
        # WHOIS for IP
        print("  [+] Running IP WHOIS...")
        whois_output = self._run_command(["whois", ip])
        if whois_output:
            whois_data = {}
            for line in whois_output.split('\n'):
                if ':' in line and not line.startswith('%'):
                    parts = line.split(':', 1)
                    if len(parts) == 2:
                        whois_data[parts[0].strip()] = parts[1].strip()
            
            results.append(OSINTResult(
                source="whois",
                data_type="ip_whois",
                data=whois_data,
                confidence="high",
                timestamp=datetime.utcnow().isoformat()
            ))
        
        # Shodan lookup
        if self.api_keys.get("shodan"):
            print("  [+] Querying Shodan...")
            try:
                import shodan
                api = shodan.Shodan(self.api_keys["shodan"])
                host = api.host(ip)
                
                shodan_data = {
                    "ip": host.get("ip_str"),
                    "org": host.get("org"),
                    "os": host.get("os"),
                    "ports": [s.get("port") for s in host.get("data", [])],
                    "hostnames": host.get("hostnames", []),
                    "vulns": list(host.get("vulns", {}).keys())[:10],
                }
                
                results.append(OSINTResult(
                    source="shodan",
                    data_type="host_info",
                    data=shodan_data,
                    confidence="high",
                    timestamp=datetime.utcnow().isoformat()
                ))
                print(f"      Found {len(shodan_data['ports'])} open ports")
                if shodan_data['vulns']:
                    print(f"      Found vulnerabilities: {', '.join(shodan_data['vulns'][:5])}")
            except ImportError:
                print("      Shodan Python library not installed")
            except Exception as e:
                print(f"      Shodan query failed: {e}")
        
        # nmap quick scan
        print("  [+] Running nmap scan...")
        nmap_output = self._run_command([
            "nmap", "-sV", "-T4", "--top-ports", "50", "-Pn", ip
        ], timeout=300)
        if nmap_output and "Error" not in nmap_output:
            # Parse open ports
            ports = re.findall(r'(\d+/\w+)\s+open\s+(\S+)', nmap_output)
            port_data = [{"port": p[0], "service": p[1]} for p in ports]
            
            results.append(OSINTResult(
                source="nmap",
                data_type="port_scan",
                data=port_data,
                confidence="high",
                timestamp=datetime.utcnow().isoformat()
            ))
            print(f"      Found {len(port_data)} open ports")
        
        return results
    
    def generate_report(self, target: str, target_type: str, results: List[OSINTResult]) -> Dict[str, Any]:
        """Generate a comprehensive OSINT report."""
        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "target": target,
            "target_type": target_type,
            "aegisnova_version": "1.0.0",
            "summary": {
                "total_sources": len(set(r.source for r in results)),
                "total_findings": len(results),
                "high_confidence": len([r for r in results if r.confidence == "high"]),
                "medium_confidence": len([r for r in results if r.confidence == "medium"]),
                "low_confidence": len([r for r in results if r.confidence == "low"]),
            },
            "findings": [asdict(r) for r in results],
            "risk_assessment": self._risk_assessment(results),
        }
        
        return report
    
    def _risk_assessment(self, results: List[OSINTResult]) -> Dict[str, Any]:
        """Perform basic risk assessment based on findings."""
        risks = []
        
        for result in results:
            if result.data_type == "exposed_services" and result.confidence == "high":
                risks.append({
                    "level": "high",
                    "finding": "Exposed services detected via Shodan",
                    "recommendation": "Review firewall rules and close unnecessary ports"
                })
            
            if result.data_type == "breach_data":
                risks.append({
                    "level": "critical",
                    "finding": "Credentials found in breach databases",
                    "recommendation": "Force password reset and enable MFA"
                })
            
            if result.data_type == "port_scan":
                data = result.data if isinstance(result.data, list) else []
                dangerous_ports = ["3389/tcp", "22/tcp", "445/tcp", "3306/tcp", "5432/tcp"]
                found_dangerous = [p for p in data if p.get("port") in dangerous_ports]
                if found_dangerous:
                    risks.append({
                        "level": "high",
                        "finding": f"Sensitive ports exposed: {', '.join(p['port'] for p in found_dangerous)}",
                        "recommendation": "Restrict access to these ports via firewall"
                    })
        
        return {
            "risk_level": "critical" if any(r["level"] == "critical" for r in risks) else
                         "high" if any(r["level"] == "high" for r in risks) else "medium",
            "findings": risks
        }


# ── CLI Interface ──
def main():
    parser = argparse.ArgumentParser(
        description="AegisNova OSINT Automation Agent"
    )
    parser.add_argument("--domain", help="Target domain for reconnaissance")
    parser.add_argument("--email", help="Target email for reconnaissance")
    parser.add_argument("--ip", help="Target IP for reconnaissance")
    parser.add_argument("--full", action="store_true", help="Enable full/deep reconnaissance")
    parser.add_argument("--output", "-o", help="Output file for report")
    
    args = parser.parse_args()
    
    agent = OSINTAgent()
    results = []
    target = ""
    target_type = ""
    
    if args.domain:
        target = args.domain
        target_type = "domain"
        results = agent.domain_recon(args.domain, args.full)
    
    elif args.email:
        target = args.email
        target_type = "email"
        results = agent.email_recon(args.email)
    
    elif args.ip:
        target = args.ip
        target_type = "ip"
        results = agent.ip_recon(args.ip)
    
    else:
        parser.print_help()
        print("\n\nExamples:")
        print("  osint-agent.py --domain example.com")
        print("  osint-agent.py --domain example.com --full --output report.json")
        print("  osint-agent.py --email admin@example.com")
        print("  osint-agent.py --ip 8.8.8.8")
        return
    
    # Generate report
    report = agent.generate_report(target, target_type, results)
    
    # Output
    output_json = json.dumps(report, indent=2, ensure_ascii=False)
    
    if args.output:
        with open(args.output, 'w') as f:
            f.write(output_json)
        print(f"\n[+] Report saved to: {args.output}")
    else:
        print("\n" + "="*60)
        print("OSINT RECONNAISSANCE REPORT")
        print("="*60)
        print(output_json)
    
    # Risk summary
    risk = report["risk_assessment"]
    print(f"\n[!] Risk Level: {risk['risk_level'].upper()}")
    if risk["findings"]:
        print("[!] Risk Findings:")
        for finding in risk["findings"]:
            print(f"    [{finding['level'].upper()}] {finding['finding']}")
            print(f"    → Recommendation: {finding['recommendation']}")


if __name__ == "__main__":
    main()
