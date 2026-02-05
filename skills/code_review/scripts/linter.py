"""Code review linter tool"""
from langchain_core.tools import tool
from pathlib import Path


@tool
def code_review_linter(file_path: str) -> str:
    """
    Run basic linting checks on a Python file.

    Args:
        file_path: Path to the Python file to lint

    Returns:
        Linting results with issues found
    """
    try:
        path = Path(file_path)
        if not path.exists():
            return f"Error: File not found: {file_path}"

        content = path.read_text(encoding="utf-8")
        issues = []

        lines = content.split("\n")
        for i, line in enumerate(lines, 1):
            # Check for line length (PEP 8: 79 chars)
            if len(line) > 79:
                issues.append(f"Line {i}: Line too long ({len(line)} > 79 chars)")

            # Check for trailing whitespace
            if line.rstrip() != line:
                issues.append(f"Line {i}: Trailing whitespace")

            # Check for tabs (should use spaces)
            if "\t" in line:
                issues.append(f"Line {i}: Contains tabs (use spaces)")

            # Check for multiple blank lines
            if i > 1 and i < len(lines) and not line.strip():
                prev_line = lines[i-2].strip()
                if not prev_line:
                    # Already counting consecutive blanks
                    pass

        # Check for missing docstring (module or first class/function)
        if lines and not lines[0].strip().startswith('"""') and not lines[0].strip().startswith("'''"):
            # Find first function or class
            for line in lines:
                if line.strip().startswith("def ") or line.strip().startswith("class "):
                    issues.append("Missing module docstring at top of file")
                    break

        if issues:
            return "Linting Issues Found:\n" + "\n".join(f"  - {issue}" for issue in issues)
        else:
            return "✓ No linting issues found"

    except Exception as e:
        return f"Error during linting: {str(e)}"