#!/usr/bin/env python3
"""Nightly drift detector.

Compares Fabric workspaces in the tenant to manifests in this repo:
  - Workspaces in tenant but not in repo  -> "unmanaged"
  - Workspaces in repo but not in tenant  -> "missing"
  - Description mismatch                   -> "drift"
  - Role-assignment mismatch              -> "role drift"

For each managed workspace (present in both repo and tenant) we compare the
*declared owners* in the manifest -- plus the provisioning service principal,
which must retain Admin -- against the *actual* workspace roleAssignments in the
tenant, reporting:
  - a declared owner missing from the workspace
  - a declared owner whose role differs from the manifest

Writes drift-report.md and exits non-zero if any drift is found.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _fabric as fab  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKSPACES_DIR = REPO_ROOT / "workspaces"


def _assignment_keys(assignment: dict) -> set[str]:
    """Candidate identifiers (lowercased) for one actual role assignment.

    A manifest owner may be given as an object id or, for users, a UPN, so we
    collect both the principal id and the user principal name when present.
    """
    principal = assignment.get("principal") or {}
    keys: set[str] = set()
    pid = principal.get("id")
    if pid:
        keys.add(str(pid).lower())
    details = principal.get("userDetails") or {}
    upn = details.get("userPrincipalName")
    if upn:
        keys.add(str(upn).lower())
    return keys


def _expected_owners(manifest: dict) -> list[dict]:
    """Desired principal -> role, from manifest owners plus the provisioner SP."""
    expected: list[dict] = []
    for o in manifest.get("owners") or []:
        ident = str(o.get("identifier", "")).strip()
        if not ident:
            continue
        expected.append({
            "type": o.get("principalType", ""),
            "identifier": ident,
            "role": o.get("role", ""),
        })
    # The provisioning service principal must retain Admin on every managed
    # workspace even though it is not listed as a manifest owner.
    sp_id = os.environ.get("AZURE_CLIENT_ID", "").strip()
    if sp_id:
        expected.append({
            "type": "ServicePrincipal",
            "identifier": sp_id,
            "role": "Admin",
        })
    return expected


def _role_findings(manifest: dict, workspace_id: str) -> list[str]:
    """Human-readable role-drift findings for a single workspace."""
    try:
        actual = fab.list_role_assignments(workspace_id)
    except Exception as exc:  # noqa: BLE001
        return [f"could not read role assignments: {exc}"]

    findings: list[str] = []
    for exp in _expected_owners(manifest):
        want = exp["identifier"].lower()
        match = next((a for a in actual if want in _assignment_keys(a)), None)
        label = f"{exp['type']} {exp['identifier']}"
        if match is None:
            findings.append(f"{label}: expected role {exp['role']}, but not assigned")
        elif (match.get("role") or "") != exp["role"]:
            findings.append(
                f"{label}: expected role {exp['role']}, found {match.get('role')}")
    return findings


def main() -> int:
    manifests = {}
    for f in sorted(WORKSPACES_DIR.glob("*.yaml")):
        m = yaml.safe_load(f.read_text())
        manifests[m["name"]] = m

    tenant = {w["displayName"]: w for w in fab.list_workspaces()
              if w.get("type") in (None, "Workspace") and w.get("displayName")}

    unmanaged = sorted(set(tenant) - set(manifests))
    missing = sorted(set(manifests) - set(tenant))
    drift = []
    role_drift: dict[str, list[str]] = {}
    for name in sorted(set(manifests) & set(tenant)):
        if (tenant[name].get("description") or "") != manifests[name]["description"]:
            drift.append(name)
        findings = _role_findings(manifests[name], tenant[name]["id"])
        if findings:
            role_drift[name] = findings

    lines = ["# Fabric Workspace Drift Report", ""]
    lines.append(f"- Manifests: {len(manifests)}")
    lines.append(f"- Tenant workspaces: {len(tenant)}")
    lines.append(f"- Unmanaged (in tenant, not in repo): **{len(unmanaged)}**")
    for n in unmanaged:
        lines.append(f"  - {n}")
    lines.append(f"- Missing (in repo, not in tenant): **{len(missing)}**")
    for n in missing:
        lines.append(f"  - {n}")
    lines.append(f"- Drifted (description mismatch): **{len(drift)}**")
    for n in drift:
        lines.append(f"  - {n}")
    lines.append(f"- Role drift (owner/role mismatch): **{len(role_drift)}**")
    for n, findings in role_drift.items():
        lines.append(f"  - {n}")
        for msg in findings:
            lines.append(f"    - {msg}")

    md = "\n".join(lines) + "\n"
    (REPO_ROOT / "drift-report.md").write_text(md)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a") as f:
            f.write(md)
    print(md)
    return 0 if not (unmanaged or missing or drift or role_drift) else 2


if __name__ == "__main__":
    sys.exit(main())
