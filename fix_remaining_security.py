#!/usr/bin/env python3
"""
Automated security fixes for remaining vulnerable endpoints.
Replaces get_current_user_flexible with require_permission for write operations.
"""
import re
import sys

# Define permission mappings for each file
PERMISSION_FIXES = {
    "MakerMatrix/routers/tag_routes.py": {
        "create_tag": "tags:create",
        "update_tag": "tags:update",
        "delete_tag": "tags:delete",
        "add_part_tag": "tags:update",
        "remove_part_tag": "tags:update",
        "add_tool_tag": "tags:update",
        "remove_tool_tag": "tags:update",
        "bulk_tag_parts": "tags:update",
        "merge_tags": "tags:update",
        "cleanup_unused_tags": "tags:delete",
    },
    "MakerMatrix/routers/label_template_routes.py": {
        "create_template": "label_templates:create",
        "update_template": "label_templates:update",
        "delete_template": "label_templates:delete",
        "duplicate_template": "label_templates:create",
        "validate_template": "label_templates:read",
    },
    "MakerMatrix/routers/import_routes.py": {
        "import_parts_from_file": "parts:create",
    },
}

def add_import_if_needed(content, filepath):
    """Add require_permission import if not present."""
    if "from MakerMatrix.auth.guards import" in content:
        # Import line exists, check if require_permission is there
        if "require_permission" not in content:
            content = content.replace(
                "from MakerMatrix.auth.guards import",
                "from MakerMatrix.auth.guards import require_permission,"
            )
    else:
        # Need to add the import line
        # Find the auth.dependencies import
        auth_dep_pattern = r"from MakerMatrix\.auth\.dependencies import.*\n"
        match = re.search(auth_dep_pattern, content)
        if match:
            insert_pos = match.end()
            content = (content[:insert_pos] +
                      "from MakerMatrix.auth.guards import require_permission\n" +
                      content[insert_pos:])
    return content

def fix_endpoint(content, function_name, permission):
    """Replace get_current_user_flexible with require_permission for a specific function."""
    # Pattern to find the function and replace the dependency
    pattern = rf"(async def {function_name}\([^)]*current_user:\s*UserModel\s*=\s*Depends\()get_current_user_flexible(\))"
    replacement = rf'\1require_permission("{permission}")\2'

    new_content, count = re.subn(pattern, replacement, content)

    if count > 0:
        print(f"  ✓ Fixed {function_name} -> {permission}")
        return new_content, True
    else:
        print(f"  ⚠ Could not find {function_name}")
        return content, False

def fix_file(filepath, fixes):
    """Apply all fixes to a file."""
    print(f"\n{'='*60}")
    print(f"Processing: {filepath}")
    print(f"{'='*60}")

    try:
        with open(filepath, 'r') as f:
            content = f.read()

        # Add import if needed
        content = add_import_if_needed(content, filepath)

        # Apply each fix
        total_fixed = 0
        for function_name, permission in fixes.items():
            content, fixed = fix_endpoint(content, function_name, permission)
            if fixed:
                total_fixed += 1

        # Write back
        with open(filepath, 'w') as f:
            f.write(content)

        print(f"\n✅ Fixed {total_fixed}/{len(fixes)} endpoints in {filepath}")
        return total_fixed

    except Exception as e:
        print(f"❌ Error processing {filepath}: {e}")
        return 0

def main():
    print("\n" + "="*60)
    print("AUTOMATED SECURITY FIX SCRIPT")
    print("="*60)
    print("Fixing remaining vulnerable endpoints...")

    total_files = len(PERMISSION_FIXES)
    total_endpoints = sum(len(fixes) for fixes in PERMISSION_FIXES.values())
    total_fixed = 0

    for filepath, fixes in PERMISSION_FIXES.items():
        fixed = fix_file(filepath, fixes)
        total_fixed += fixed

    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Files processed: {total_files}")
    print(f"Endpoints fixed: {total_fixed}/{total_endpoints}")

    if total_fixed == total_endpoints:
        print("\n✅ ALL ENDPOINTS SECURED!")
        return 0
    else:
        print(f"\n⚠️  {total_endpoints - total_fixed} endpoints may need manual review")
        return 1

if __name__ == "__main__":
    sys.exit(main())
