from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict

from langchain_core.tools import tool


@tool
def run_python_code_tool(code: str) -> Dict[str, Any]:
    """Execute generated Python code in an isolated subprocess with a 30s timeout."""
    payload = {
        "output": "",
        "error": None,
        "dataframe_shape": None,
    }

    wrapper = (
        "import json\n"
        "_locals = {}\n"
        f"exec({code!r}, {{}}, _locals)\n"
        "result = _locals.get('result')\n"
        "df = _locals.get('df')\n"
        "shape = tuple(df.shape) if hasattr(df, 'shape') else None\n"
        "print(json.dumps({'result': result, 'dataframe_shape': shape}, default=str))\n"
    )

    with tempfile.TemporaryDirectory(prefix="dataverse_exec_") as tmp_dir:
        script_path = Path(tmp_dir) / "runner.py"
        script_path.write_text(wrapper, encoding="utf-8")

        try:
            proc = subprocess.run(
                [sys.executable, str(script_path)],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
        except subprocess.TimeoutExpired:
            payload["error"] = "Execution timed out after 30 seconds"
            return payload

        if proc.returncode != 0:
            payload["error"] = proc.stderr.strip() or "Python execution failed"
            return payload

        stdout = proc.stdout.strip().splitlines()
        if not stdout:
            payload["output"] = ""
            return payload

        try:
            parsed = json.loads(stdout[-1])
            payload["output"] = parsed.get("result")
            payload["dataframe_shape"] = parsed.get("dataframe_shape")
            return payload
        except json.JSONDecodeError:
            payload["output"] = proc.stdout.strip()
            return payload
