#!/bin/bash
# Remove leaked API keys from git history
# This rewrites git history - coordinate with team first!

set -e

echo "⚠️  WARNING: This will rewrite git history!"
echo "All team members will need to re-clone the repository."
echo ""
read -p "Continue? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

# Backup
echo "Creating backup..."
BACKUP_DIR="../MakerMatrix_backup_$(date +%Y%m%d_%H%M%S)"
cp -r . "$BACKUP_DIR"
echo "✓ Backup: $BACKUP_DIR"

# Install git-filter-repo if needed
if ! command -v git-filter-repo &> /dev/null; then
    echo "Installing git-filter-repo..."
    pip install git-filter-repo
fi

# Create replacement file for both leaked keys
cat > /tmp/api_keys_to_remove.txt << 'EOF'
REDACTED_API_KEY==>REDACTED_API_KEY
REDACTED_API_KEY==>REDACTED_API_KEY
EOF

echo "Removing API keys from git history..."
git filter-repo --replace-text /tmp/api_keys_to_remove.txt --force

# Remove database backup files from history
echo "Removing sensitive database files from git history..."
git filter-repo --invert-paths --path makermatrix.db.backup_20251012_175714 --force

# Verify removal
echo "Verifying API key removal..."
if git log --all -S "mm_Z8p_" | grep -q "commit" || git log --all -S "mm_hwV" | grep -q "commit"; then
    echo "❌ Keys still found in history!"
    exit 1
fi

echo "Verifying database backup removal..."
if git log --all --name-only --pretty=format: | grep -q "makermatrix.db.backup"; then
    echo "❌ Database backup still found in history!"
    exit 1
fi

rm /tmp/api_keys_to_remove.txt
echo "✓ Done!"
echo ""
echo "Next steps:"
echo "1. git push origin --force --all"
echo "2. git push origin --force --tags"
echo "3. Notify team to re-clone"
