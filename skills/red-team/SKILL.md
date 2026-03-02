---
id: red-team-qa
name: Red Team QA Agent
description: Automated security testing and vulnerability detection for OpenPango agents
version: 1.0.0
author: Atlas
bounty: "#36"
---

# Red Team QA Agent Skill

## Overview

This skill provides automated security testing capabilities for the OpenPango ecosystem. It acts as a QA-Red-Team sub-agent that aggressively tests, breaks, and finds security flaws in the outputs of other agents.

## Features

- **SQL Injection Detection**: Scans for unsafe SQL query patterns
- **XSS Vulnerability Scanning**: Detects cross-site scripting vulnerabilities
- **Authentication Bypass Detection**: Identifies weak auth patterns
- **Command Injection Testing**: Finds unsafe command execution
- **Structured Reporting**: Outputs JSON reports for orchestrator integration

## Installation

```bash
# Copy to skills directory
cp -r skills/red-team /path/to/openpango/skills/
```

## Usage

### Command Line

```bash
python qa_tester.py /path/to/target/code
```

### As OpenPango Skill

The skill is automatically invoked by the Orchestrator after the Coder agent completes a task.

## Configuration

No additional configuration required. The skill works out of the box.

## Output Format

```json
{
  "scan_completed": true,
  "vulnerabilities_found": 5,
  "critical_count": 2,
  "high_count": 2,
  "medium_count": 1,
  "vulnerabilities": [
    {
      "severity": "critical",
      "category": "sql_injection",
      "file": "/path/to/file.py",
      "line": 42,
      "evidence": "cursor.execute(query + user_input)",
      "timestamp": "2026-03-02T12:00:00"
    }
  ]
}
```

## Exit Codes

- `0`: No critical vulnerabilities found
- `1`: Critical vulnerabilities detected (blocks Coder output)

## Dependencies

- Python 3.8+
- Standard library only (no external dependencies)

## License

MIT
