#!/usr/bin/env python3
"""
Red Teaming & QA Agent Skill
Bounty #36 - $13

This agent aggressively tests, breaks, and finds security flaws
in the outputs of other agents.
"""

import json
import os
import sys
import re
from typing import Dict, List
from datetime import datetime


class RedTeamAgent:
    """QA-Red-Team sub-agent for security testing."""
    
    def __init__(self, target_path: str):
        self.target_path = target_path
        self.vulnerabilities: List[Dict] = []
        
    def run_security_scan(self) -> Dict:
        """Run comprehensive security scan on target code."""
        print(f"[*] Starting security scan on: {self.target_path}")
        
        self._test_sql_injection()
        self._test_xss()
        self._test_auth_bypass()
        self._test_command_injection()
        
        return {
            "scan_completed": True,
            "vulnerabilities_found": len(self.vulnerabilities),
            "critical_count": len([v for v in self.vulnerabilities if v["severity"] == "critical"]),
            "high_count": len([v for v in self.vulnerabilities if v["severity"] == "high"]),
            "medium_count": len([v for v in self.vulnerabilities if v["severity"] == "medium"]),
            "low_count": len([v for v in self.vulnerabilities if v["severity"] == "low"]),
            "vulnerabilities": self.vulnerabilities,
            "timestamp": datetime.now().isoformat()
        }
    
    def _test_sql_injection(self):
        """Test for SQL injection vulnerabilities."""
        print("[*] Testing SQL injection...")
        
        patterns = [
            r"\.execute\s*\(\s*[^,)]*\+",
            r"\.query\s*\(\s*[^,)]*\+",
            r"f\".*SELECT.*\{.*\}.*\"",
            r"f'.*SELECT.*\{.*\}.*'"
        ]
        
        self._scan_patterns(patterns, "sql_injection", "critical")
    
    def _test_xss(self):
        """Test for XSS vulnerabilities."""
        print("[*] Testing XSS...")
        
        patterns = [
            r"innerHTML\s*=",
            r"document\.write\s*\(",
            r"\.html\s*\(",
            r"dangerouslySetInnerHTML"
        ]
        
        self._scan_patterns(patterns, "xss", "high")
    
    def _test_auth_bypass(self):
        """Test for authentication bypass vulnerabilities."""
        print("[*] Testing auth bypass...")
        
        patterns = [
            r"password\s*=\s*['\"][^'\"]{0,30}['\"]",
            r"api_key\s*=\s*['\"][^'\"]{0,30}['\"]",
            r"secret\s*=\s*['\"][^'\"]{0,30}['\"]"
        ]
        
        self._scan_patterns(patterns, "auth_bypass", "critical")
    
    def _test_command_injection(self):
        """Test for command injection vulnerabilities."""
        print("[*] Testing command injection...")
        
        patterns = [
            r"os\.system\s*\(",
            r"subprocess\.call\s*\([^)]*\+",
            r"subprocess\.run\s*\([^)]*\+",
            r"exec\s*\([^)]*\+",
            r"eval\s*\([^)]*\+"
        ]
        
        self._scan_patterns(patterns, "command_injection", "critical")
    
    def _scan_patterns(self, patterns: List[str], category: str, severity: str):
        """Scan code for given regex patterns."""
        for root, dirs, files in os.walk(self.target_path):
            # Skip hidden directories and common non-code directories
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', '__pycache__', 'venv', '.git']]
            
            for file in files:
                if file.endswith(('.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.go')):
                    filepath = os.path.join(root, file)
                    try:
                        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            for pattern in patterns:
                                matches = re.finditer(pattern, content, re.IGNORECASE)
                                for match in matches:
                                    line_num = content[:match.start()].count('\n') + 1
                                    self.vulnerabilities.append({
                                        "severity": severity,
                                        "category": category,
                                        "file": filepath,
                                        "line": line_num,
                                        "evidence": match.group()[:100],
                                        "timestamp": datetime.now().isoformat()
                                    })
                    except (IOError, OSError) as e:
                        print(f"[!] Error reading {filepath}: {e}")
                        continue
    
    def generate_report(self) -> str:
        """Generate human-readable security report."""
        report = []
        report.append("=" * 60)
        report.append("🔴 RED TEAM SECURITY AUDIT REPORT")
        report.append("=" * 60)
        report.append(f"Target: {self.target_path}")
        report.append(f"Scan Time: {datetime.now().isoformat()}")
        report.append(f"Total Vulnerabilities: {len(self.vulnerabilities)}")
        report.append("")
        
        # Group by severity
        critical = [v for v in self.vulnerabilities if v["severity"] == "critical"]
        high = [v for v in self.vulnerabilities if v["severity"] == "high"]
        medium = [v for v in self.vulnerabilities if v["severity"] == "medium"]
        
        if critical:
            report.append(f"\n🔴 CRITICAL ({len(critical)}):")
            for v in critical:
                report.append(f"  [{v['category']}] {v['file']}:{v['line']}")
        
        if high:
            report.append(f"\n🟠 HIGH ({len(high)}):")
            for v in high:
                report.append(f"  [{v['category']}] {v['file']}:{v['line']}")
        
        if medium:
            report.append(f"\n🟡 MEDIUM ({len(medium)}):")
            for v in medium:
                report.append(f"  [{v['category']}] {v['file']}:{v['line']}")
        
        if not self.vulnerabilities:
            report.append("\n✅ No vulnerabilities detected!")
        
        report.append("\n" + "=" * 60)
        
        return "\n".join(report)


def main():
    """CLI entry point for Red Team Agent."""
    if len(sys.argv) < 2:
        print("Usage: python qa_tester.py <target_path>")
        sys.exit(1)
    
    target = sys.argv[1]
    
    if not os.path.exists(target):
        print(f"Error: Target path '{target}' does not exist")
        sys.exit(1)
    
    agent = RedTeamAgent(target)
    results = agent.run_security_scan()
    
    # Print report
    print(agent.generate_report())
    
    # Output JSON for orchestrator
    print("\n--- JSON OUTPUT ---")
    print(json.dumps(results, indent=2))
    
    # Return exit code based on critical findings
    critical_count = results.get("critical_count", 0)
    if critical_count > 0:
        sys.exit(1)  # Fail if critical vulnerabilities found
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
