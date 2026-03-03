# Skill Security Scanner CI Baseline

This document defines expected behavior for `.github/workflows/skill-security-scan.yml`.

## Trigger Matrix

- **pull_request** with changes under `skills/**` → should run
- **push to main** with changes under `skills/**` → should run
- **workflow_dispatch** → should run manually (for validation/recovery)

## Required Scripts

The workflow expects both scripts to exist:

- `scripts/ci-scan.js`
- `scripts/sandbox-test.js`

If either file is missing, CI will fail before meaningful security validation.

## Expected Outcomes

- No changed skills:
  - SAST: pass (`No skills to scan`)
  - Sandbox: pass/skip (`No skills to sandbox test`)
  - Final gate: pass
- Changed skills with violations:
  - Either SAST or Sandbox step may fail
  - Final gate **must fail**

## Quick Triage for Failures

1. Check failed step name in run summary.
2. If failure is `MODULE_NOT_FOUND`, verify script paths above.
3. If final gate failed, inspect outcomes of:
   - `Run SAST + CVE scan on changed skills`
   - `Sandbox execution test`
4. Re-run using `workflow_dispatch` after fix.
