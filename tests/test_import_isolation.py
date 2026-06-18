"""Import-isolation gate (SPEC §3 hard rule).

Each core module must import in a *clean* interpreter without dragging in the
optional CLI/MCP layers or heavy/test-only dependencies. The check runs in a
fresh subprocess (``python -c ...``) so it cannot be masked by imports that
other tests have already performed in this interpreter.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys

import pytest

# Modules that must NEVER be loaded as a side effect of importing core Veritas:
# the optional layers (veritas.cli / veritas.mcp), the typer CLI library, the
# MCP SDK (``mcp``), and the test-only scikit-learn dependency.
FORBIDDEN_MODULES: tuple[str, ...] = (
    "veritas.cli",
    "veritas.mcp",
    "typer",
    "mcp",
    "sklearn",
)

# Core modules that must satisfy the isolation rule. ADD EVERY NEW CORE MODULE
# HERE as it is created. Modules that do not exist yet are skipped (not failed),
# so this list may be populated ahead of implementation. The optional layers
# (veritas.cli / veritas.mcp) are deliberately absent — they are not core.
CORE_MODULES: tuple[str, ...] = (
    "veritas",
    "veritas.config",
    "veritas.contracts",
    "veritas.io",
    "veritas.contamination",
    "veritas.metrics",
    "veritas.stratify",
    "veritas.provenance",
    "veritas.report",
    "veritas.audit",
)

# Probe executed in a pristine interpreter: import the target module, then print
# (comma-separated, to stdout) any forbidden modules that ended up loaded.
_ISOLATION_PROBE = """
import importlib
import json
import sys

target, forbidden = sys.argv[1], json.loads(sys.argv[2])
importlib.import_module(target)
leaked = sorted(name for name in forbidden if name in sys.modules)
sys.stdout.write(",".join(leaked))
"""


def _module_exists(module: str) -> bool:
    try:
        return importlib.util.find_spec(module) is not None
    except ModuleNotFoundError:
        return False


@pytest.mark.parametrize("module", CORE_MODULES)
def test_core_module_imports_without_optional_layers(module: str) -> None:
    if not _module_exists(module):
        pytest.skip(f"{module} not implemented yet")

    result = subprocess.run(
        [sys.executable, "-c", _ISOLATION_PROBE, module, json.dumps(FORBIDDEN_MODULES)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, (
        f"importing {module} in a clean interpreter failed:\n{result.stderr}"
    )
    leaked = [name for name in result.stdout.strip().split(",") if name]
    assert leaked == [], f"importing {module} leaked optional dependencies: {leaked}"
