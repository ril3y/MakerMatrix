#!/usr/bin/env python3
"""
Dead Code Analysis Script for MakerMatrix
Runs vulture for Python and ts-unused-exports for TypeScript/React
"""

import subprocess
import sys
import os
from pathlib import Path
from datetime import datetime


def run_command(cmd, cwd=None, capture_output=True):
    """Run a command and return the result"""
    try:
        result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=capture_output, text=True)
        return result
    except Exception as e:
        print(f"Error running command '{cmd}': {e}")
        return None


def analyze_python_dead_code():
    """Run vulture analysis on Python code"""
    print("🐍 Running Python dead code analysis with vulture...")

    # Change to project root
    project_root = Path(__file__).parent.parent

    # Run vulture with configuration using bash explicitly
    cmd = "/bin/bash -c 'source venv_test/bin/activate && vulture MakerMatrix/ --min-confidence 80 --sort-by-size'"
    result = run_command(cmd, cwd=project_root)

    if result and result.returncode == 0:
        print("✅ Python analysis completed successfully")
        if result.stdout.strip():
            print("📝 Found potential dead code:")
            print(result.stdout)
            return result.stdout
        else:
            print("🎉 No dead code found!")
            return "No dead code detected"
    else:
        print("❌ Python analysis failed")
        if result and result.stderr:
            print(f"Error: {result.stderr}")
        return "Analysis failed"


def analyze_typescript_dead_code():
    """Run ts-unused-exports analysis on TypeScript/React code"""
    print("🔷 Running TypeScript dead code analysis...")

    # Change to frontend directory
    frontend_dir = Path(__file__).parent.parent / "MakerMatrix" / "frontend"

    # Run ts-unused-exports
    cmd = 'npx ts-unused-exports tsconfig.json --excludePathsFromReport="node_modules;dist;coverage;__tests__;tests"'
    result = run_command(cmd, cwd=frontend_dir)

    if result:
        if result.returncode == 0:
            print("✅ TypeScript analysis completed successfully")
            if result.stdout.strip():
                print("📝 Found unused exports:")
                print(result.stdout)
                return result.stdout
            else:
                print("🎉 No unused exports found!")
                return "No unused exports detected"
        else:
            # ts-unused-exports returns non-zero when it finds unused exports
            if result.stdout.strip():
                print("📝 Found unused exports:")
                print(result.stdout)
                return result.stdout
            else:
                print("❌ TypeScript analysis failed")
                if result.stderr:
                    print(f"Error: {result.stderr}")
                return "Analysis failed"
    else:
        return "Analysis failed"


def generate_report(python_results, typescript_results):
    """Generate a comprehensive dead code analysis report"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    report = f"""
# Dead Code Analysis Report
Generated: {timestamp}

## Python Dead Code Analysis (vulture)
{python_results}

## TypeScript Dead Code Analysis (ts-unused-exports)  
{typescript_results}

## Recommendations
1. Review identified dead code carefully before removal
2. Check if code is used in tests or configuration files
3. Verify code isn't used dynamically (string imports, etc.)
4. Consider if code is part of public API that shouldn't be removed
5. Run all tests after removing dead code to ensure nothing breaks

## False Positives
Some results may be false positives:
- Test fixtures used by pytest
- Code used in decorators or middleware
- Dynamic imports or string-based imports
- Public API exports that are meant to be used externally
- Code used in configuration files
"""

    # Save report to file
    report_path = Path(__file__).parent.parent / "dead_code_analysis_report.md"
    with open(report_path, "w") as f:
        f.write(report)

    print(f"📄 Report saved to: {report_path}")
    return report


def main():
    """Main function to run dead code analysis"""
    print("🔍 Starting Dead Code Analysis for MakerMatrix")
    print("=" * 50)

    # Run Python analysis
    python_results = analyze_python_dead_code()
    print("\n" + "=" * 50)

    # Run TypeScript analysis
    typescript_results = analyze_typescript_dead_code()
    print("\n" + "=" * 50)

    # Generate report
    report = generate_report(python_results, typescript_results)

    print("\n🎯 Dead Code Analysis Complete!")
    print("📋 Next steps:")
    print("1. Review the generated report")
    print("2. Carefully examine identified dead code")
    print("3. Remove confirmed dead code")
    print("4. Run tests to ensure nothing breaks")
    print("5. Update vulture.toml and .ts-unused-exports.json to ignore false positives")


if __name__ == "__main__":
    main()
