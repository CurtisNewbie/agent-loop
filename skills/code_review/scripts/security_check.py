"""Code review security check tool"""
import re
from pathlib import Path


def code_review_security_check(file_path: str) -> str:
    """
    Check for common security vulnerabilities in Python code.

    Args:
        file_path: Path to the Python file to check

    Returns:
        Security issues found with severity levels
    """
    try:
        path = Path(file_path)
        if not path.exists():
            return f"Error: File not found: {file_path}"

        content = path.read_text(encoding="utf-8")
        issues = []

        # Check for hardcoded passwords/secrets
        secret_patterns = [
            (r'password\s*=\s*["\'].*["\']', "CRITICAL: Hardcoded password"),
            (r'api_key\s*=\s*["\'].*["\']', "HIGH: Hardcoded API key"),
            (r'secret\s*=\s*["\'].*["\']', "HIGH: Hardcoded secret"),
            (r'token\s*=\s*["\'].*["\']', "HIGH: Hardcoded token"),
        ]

        for pattern, message in secret_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                line_num = content[:match.start()].count("\n") + 1
                issues.append(f"Line {line_num}: {message}")

        # Check for SQL injection risks
        sql_patterns = [
            (r'execute\s*\(\s*["\'].*%s.*["\']', "WARNING: Potential SQL injection with string formatting"),
            (r'execute\s*\(\s*["\'].*\{.*\}.*["\']', "WARNING: Potential SQL injection with f-string"),
        ]

        for pattern, message in sql_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                line_num = content[:match.start()].count("\n") + 1
                issues.append(f"Line {line_num}: {message}")

        # Check for eval/exec usage
        dangerous_functions = [
            (r'\beval\s*\(', "CRITICAL: eval() usage - dangerous"),
            (r'\bexec\s*\(', "CRITICAL: exec() usage - dangerous"),
            (r'\bcompile\s*\([^,]*,\s*["\']eval["\']', "HIGH: compile() with 'eval' mode"),
        ]

        for pattern, message in dangerous_functions:
            matches = re.finditer(pattern, content)
            for match in matches:
                line_num = content[:match.start()].count("\n") + 1
                issues.append(f"Line {line_num}: {message}")

        # Check for shell injection risks
        shell_patterns = [
            (r'subprocess\.(call|run|Popen)\s*\(\s*["\'].*\$\{.*\}.*["\']', "HIGH: Shell injection with ${var}"),
            (r'subprocess\.(call|run|Popen)\s*\(\s*["\'].*%s.*["\']\s*,\s*shell\s*=\s*True', "CRITICAL: Shell=True with string formatting"),
            (r'os\.system\s*\(', "HIGH: os.system() usage - consider subprocess"),
        ]

        for pattern, message in shell_patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                line_num = content[:match.start()].count("\n") + 1
                issues.append(f"Line {line_num}: {message}")

        # Check for weak hash functions
        weak_hashes = [
            (r'md5\s*\(', "INFO: MD5 hash - consider SHA-256+"),
            (r'sha1\s*\(', "INFO: SHA1 hash - consider SHA-256+"),
        ]

        for pattern, message in weak_hashes:
            matches = re.finditer(pattern, content)
            for match in matches:
                line_num = content[:match.start()].count("\n") + 1
                issues.append(f"Line {line_num}: {message}")

        # Check for random usage for security
        random_issues = [
            (r'\bimport\s+random\b', "WARNING: random module not cryptographically secure - use secrets"),
            (r'from\s+random\s+import', "WARNING: random module not cryptographically secure - use secrets"),
        ]

        for pattern, message in random_issues:
            matches = re.finditer(pattern, content)
            for match in matches:
                line_num = content[:match.start()].count("\n") + 1
                issues.append(f"Line {line_num}: {message}")

        # Check for pickle usage (can execute arbitrary code)
        pickle_patterns = [
            (r'pickle\.loads?\s*\(', "HIGH: pickle usage - can execute arbitrary code"),
        ]

        for pattern, message in pickle_patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                line_num = content[:match.start()].count("\n") + 1
                issues.append(f"Line {line_num}: {message}")

        if issues:
            return "Security Issues Found:\n" + "\n".join(f"  - {issue}" for issue in issues)
        else:
            return "✓ No obvious security vulnerabilities found"

    except Exception as e:
        return f"Error during security check: {str(e)}"