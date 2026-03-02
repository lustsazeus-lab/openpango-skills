---
name: data-analysis
description: "Sandboxed Python data analysis execution with CSV/JSON inputs, restricted IO/network, and base64 chart outputs."
version: "1.0.0"
user-invocable: true
metadata:
  capabilities:
    - data/analysis
    - data/csv-json
    - data/charts
    - security/sandbox
  author: "Antigravity (OpenPango Core)"
  license: "MIT"
---

# Data Analysis Sandbox Skill

`skills/data-analysis/sandbox.py` provides a Jupyter-like execution sandbox for autonomous agents.

## What it does

- Runs untrusted Python analysis scripts in an isolated subprocess (`python -I`)
- Enforces timeout + resource limits (CPU/memory/file descriptors where supported)
- Mounts only CSV/JSON inputs into sandbox `input/`
- Captures `stdout` and `stderr`
- Returns generated chart artifacts (`png/jpg/jpeg/webp/svg`) as base64
- Blocks common network/process breakout paths and file writes outside sandbox output

## Example

```python
from pathlib import Path
import importlib.util

sandbox_path = Path("skills/data-analysis/sandbox.py")
spec = importlib.util.spec_from_file_location("data_analysis_sandbox", sandbox_path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

sandbox = mod.DataAnalysisSandbox()
result = sandbox.execute(
    """
import os
import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv(os.path.join(INPUT_DIR, 'sales.csv'))
print(df.describe().to_string())

plt.figure(figsize=(6, 3))
plt.plot(df['revenue'])
plt.title('Revenue trend')
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, 'revenue.png'))
""",
    input_files=["./sales.csv"],
)

print(result["stdout"])
print(result["charts"][0]["base64"][:80])
```

## Security Notes

This sandbox adds strong application-layer restrictions but is not equivalent to a full container VM boundary. For high-risk multi-tenant use, run this inside a container/sandbox runtime as an additional isolation layer.
