#!/bin/bash
# MakerMatrix Docker Build Script

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}Building MakerMatrix Docker Image${NC}"
echo ""

# Get version from __init__.py
VERSION=$(grep -oP '__version__\s*=\s*"\K[^"]+' MakerMatrix/__init__.py)
echo -e "${GREEN}Version:${NC} $VERSION"

# Get build date
BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
echo -e "${GREEN}Build Date:${NC} $BUILD_DATE"

# Get git commit
if git rev-parse --short HEAD >/dev/null 2>&1; then
    VCS_REF=$(git rev-parse --short HEAD)
else
    VCS_REF="local"
fi
echo -e "${GREEN}Git Ref:${NC} $VCS_REF"

echo ""
echo -e "${BLUE}Starting build...${NC}"
echo ""

# Build the image
docker build \
    --build-arg VERSION="$VERSION" \
    --build-arg BUILD_DATE="$BUILD_DATE" \
    --build-arg VCS_REF="$VCS_REF" \
    -t makermatrix:latest \
    -t makermatrix:$VERSION \
    -t makermatrix:dev \
    .

echo ""
echo -e "${GREEN}✓ Build complete!${NC}"
echo ""
echo "Image tags:"
echo "  - makermatrix:latest"
echo "  - makermatrix:$VERSION"
echo "  - makermatrix:dev"
echo ""
echo "Test the image:"
echo "  docker run --rm makermatrix:latest python -c \"import MakerMatrix; print(f'MakerMatrix v{MakerMatrix.__version__}')\""
echo ""
echo "Run the container:"
echo "  docker run -d -p 8080:8080 -v makermatrix-data:/data makermatrix:latest"
echo ""
