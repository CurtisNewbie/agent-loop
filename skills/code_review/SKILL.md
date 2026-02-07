---
name: code_review
description: Perform comprehensive code review with security analysis
allowed-tools: "read_file, list_directory, code_review_linter, code_review_security_check"
version: 1.0.0
license: MIT
---

# Code Review Skill

## Purpose
Perform comprehensive code review including style checking, security analysis, and best practices verification.

## When to Use
- User asks to review code
- User mentions "code review", "check code", "analyze code"
- User wants to improve code quality

## Instructions

### Step 1: Understand the Code
1. Read the target file using the read_file tool
2. Identify the programming language
3. Understand the code's purpose and structure

### Step 2: Style Review
Check for:
- Consistent indentation and formatting
- Naming conventions
- Comment quality and coverage
- Code organization

### Step 3: Security Review
Look for:
- SQL injection vulnerabilities
- XSS risks
- Hardcoded secrets or credentials
- Input validation issues
- Authentication/authorization problems

### Step 4: Best Practices
Verify:
- Error handling
- Resource management
- Performance considerations
- Test coverage
- Documentation

### Step 5: Generate Report
Provide:
- Overall summary
- Critical issues (with line numbers)
- Suggestions for improvement
- Priority ranking of issues

## Examples

### Example 1: Basic Review
User: "Review the authentication module in app/auth.py"
You should:
1. Read app/auth.py
2. Apply all review steps
3. Generate comprehensive report

### Example 2: Security Focus
User: "Check for security issues in payment processing"
You should:
1. Focus primarily on Step 3 (Security Review)
2. Prioritize security-related findings
3. Provide remediation suggestions

## Notes
- Always provide line numbers for issues
- Suggest specific fixes, not just point out problems
- Be constructive and helpful
- If code is too large, ask user which sections to focus on