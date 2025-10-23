#!/usr/bin/env python3
"""
Static analysis script to check API route consistency.
This can be run as part of CI/CD pipeline for early detection of issues.
"""

import ast
import os
import sys
from pathlib import Path
from typing import List, Dict, Any


class APIConsistencyChecker(ast.NodeVisitor):
    """AST visitor to check API route consistency."""

    def __init__(self):
        self.issues = []
        self.current_file = None
        self.route_functions = []

    def check_file(self, file_path: Path):
        """Check a single Python file for API consistency issues."""
        self.current_file = file_path
        self.route_functions = []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content)
            self.visit(tree)

        except Exception as e:
            self.issues.append(
                {"file": str(file_path), "line": 0, "issue": f"Failed to parse file: {e}", "severity": "error"}
            )

    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Visit function definitions to check for route handlers."""
        # Check if this function has router decorators
        has_route_decorator = False

        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Attribute):
                # Handle @router.get, @router.post, etc.
                if (
                    isinstance(decorator.value, ast.Name)
                    and decorator.value.id == "router"
                    and decorator.attr in ["get", "post", "put", "delete", "patch"]
                ):
                    has_route_decorator = True
                    break
            elif isinstance(decorator, ast.Call):
                # Handle @router.get(), @router.post(), etc.
                if (
                    isinstance(decorator.func, ast.Attribute)
                    and isinstance(decorator.func.value, ast.Name)
                    and decorator.func.value.id == "router"
                    and decorator.func.attr in ["get", "post", "put", "delete", "patch"]
                ):
                    has_route_decorator = True
                    break

        if has_route_decorator:
            self.route_functions.append(node)
            self.check_route_function(node)

        self.generic_visit(node)

    def check_route_function(self, node: ast.FunctionDef):
        """Check a route function for consistency issues."""
        func_name = node.name

        # Skip allowed exceptions
        allowed_exceptions = {
            "get_image",
            "serve_index_html",
            "upload_image",
            "get_current_user",
            "serve_frontend",
            "websocket_endpoint",
            "download_backup",
            "export_data",
        }

        if func_name in allowed_exceptions:
            return

        # Check return type annotation
        if node.returns is None:
            self.issues.append(
                {
                    "file": str(self.current_file),
                    "line": node.lineno,
                    "function": func_name,
                    "issue": "Route function missing return type annotation",
                    "severity": "warning",
                }
            )
            return

        # Check if return type is ResponseSchema
        return_type_name = self.get_type_name(node.returns)

        if not return_type_name.startswith("ResponseSchema"):
            self.issues.append(
                {
                    "file": str(self.current_file),
                    "line": node.lineno,
                    "function": func_name,
                    "issue": f"Route function should return ResponseSchema, got {return_type_name}",
                    "severity": "error",
                }
            )

        # Check for return statements
        self.check_return_statements(node, func_name)

    def check_return_statements(self, node: ast.FunctionDef, func_name: str):
        """Check return statements within a route function."""
        for stmt in ast.walk(node):
            if isinstance(stmt, ast.Return) and stmt.value:
                # Check if return value constructs ResponseSchema
                if isinstance(stmt.value, ast.Call):
                    call_name = self.get_call_name(stmt.value)
                    if not call_name.endswith("ResponseSchema"):
                        self.issues.append(
                            {
                                "file": str(self.current_file),
                                "line": stmt.lineno,
                                "function": func_name,
                                "issue": f"Return statement should construct ResponseSchema, found {call_name}",
                                "severity": "warning",
                            }
                        )
                elif not isinstance(stmt.value, ast.Name):
                    # Direct return of dict or other non-ResponseSchema
                    self.issues.append(
                        {
                            "file": str(self.current_file),
                            "line": stmt.lineno,
                            "function": func_name,
                            "issue": "Return statement should return ResponseSchema instance",
                            "severity": "warning",
                        }
                    )

    def get_type_name(self, node: ast.AST) -> str:
        """Extract type name from AST node."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Subscript):
            base_name = self.get_type_name(node.value)
            return f"{base_name}[...]"
        elif isinstance(node, ast.Attribute):
            return f"{self.get_type_name(node.value)}.{node.attr}"
        else:
            return str(type(node).__name__)

    def get_call_name(self, node: ast.Call) -> str:
        """Extract function call name from AST node."""
        if isinstance(node.func, ast.Name):
            return node.func.id
        elif isinstance(node.func, ast.Attribute):
            return (
                f"{self.get_call_name(node.func.value) if hasattr(node.func.value, 'id') else '...'}.{node.func.attr}"
            )
        else:
            return "unknown"


def check_api_consistency(routers_dir: Path) -> List[Dict[str, Any]]:
    """Check API consistency for all router files."""
    checker = APIConsistencyChecker()

    # Find all Python files in routers directory
    for py_file in routers_dir.glob("*.py"):
        if py_file.name == "__init__.py":
            continue

        checker.check_file(py_file)

    return checker.issues


def main():
    """Main function for CLI usage."""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    routers_dir = project_root / "MakerMatrix" / "routers"

    if not routers_dir.exists():
        print(f"Error: Routers directory not found at {routers_dir}")
        sys.exit(1)

    print("Checking API consistency...")
    issues = check_api_consistency(routers_dir)

    if not issues:
        print("✅ All API routes follow consistent ResponseSchema pattern!")
        sys.exit(0)

    print(f"❌ Found {len(issues)} API consistency issues:\n")

    # Group issues by severity
    errors = [issue for issue in issues if issue["severity"] == "error"]
    warnings = [issue for issue in issues if issue["severity"] == "warning"]

    if errors:
        print("🚨 ERRORS (must fix):")
        for issue in errors:
            print(f"  {issue['file']}:{issue['line']} - {issue['issue']}")
        print()

    if warnings:
        print("⚠️  WARNINGS (should fix):")
        for issue in warnings:
            print(f"  {issue['file']}:{issue['line']} - {issue['issue']}")
        print()

    # Exit with error code if there are errors
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
