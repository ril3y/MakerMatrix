#!/bin/bash
# MakerMatrix Quick Start Script
# Pulls and runs MakerMatrix from GitHub Container Registry

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
IMAGE_NAME="ghcr.io/ril3y/makermatrix"
CONTAINER_NAME="makermatrix"
VOLUME_NAME="makermatrix-data"
PORT="${MAKERMATRIX_PORT:-8080}"

echo -e "${BLUE}╔════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     MakerMatrix Quick Start Script        ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════╝${NC}"
echo ""

# Function to print colored messages
print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first:"
    echo "  https://docs.docker.com/get-docker/"
    exit 1
fi

print_success "Docker is installed"

# Check if container is already running
if docker ps | grep -q "$CONTAINER_NAME"; then
    print_warning "MakerMatrix is already running!"
    echo ""
    echo "Available commands:"
    echo "  Stop:    docker stop $CONTAINER_NAME"
    echo "  Restart: docker restart $CONTAINER_NAME"
    echo "  Logs:    docker logs -f $CONTAINER_NAME"
    echo "  Remove:  docker stop $CONTAINER_NAME && docker rm $CONTAINER_NAME"
    echo ""
    echo "Access at: http://localhost:$PORT"
    exit 0
fi

# Prompt for image tag
echo ""
print_info "Select image version to pull:"
echo "  1) latest (recommended - stable release)"
echo "  2) main (latest development build)"
echo "  3) Specific version (e.g., v1.0.0)"
echo ""
read -p "Enter choice [1-3] (default: 1): " version_choice

case $version_choice in
    2)
        IMAGE_TAG="main"
        ;;
    3)
        read -p "Enter version tag (e.g., v1.0.0): " custom_tag
        IMAGE_TAG="$custom_tag"
        ;;
    *)
        IMAGE_TAG="latest"
        ;;
esac

FULL_IMAGE="$IMAGE_NAME:$IMAGE_TAG"

# Pull the image
echo ""
print_info "Pulling $FULL_IMAGE..."
if docker pull "$FULL_IMAGE"; then
    print_success "Image pulled successfully"
else
    print_error "Failed to pull image. Check your internet connection and try again."
    exit 1
fi

# Create volume if it doesn't exist
if ! docker volume inspect "$VOLUME_NAME" &> /dev/null; then
    print_info "Creating Docker volume: $VOLUME_NAME"
    docker volume create "$VOLUME_NAME"
    print_success "Volume created"
else
    print_success "Using existing volume: $VOLUME_NAME"
fi

# Prompt for JWT secret
echo ""
print_warning "Security Configuration"
echo "A secure JWT secret key is required for production use."
echo ""
read -p "Enter JWT secret key (or press Enter to generate one): " jwt_secret

if [ -z "$jwt_secret" ]; then
    # Generate a random secret
    jwt_secret=$(openssl rand -hex 32 2>/dev/null || head -c 32 /dev/urandom | base64)
    print_success "Generated random JWT secret"
fi

# Optional: Prompt for supplier API keys
echo ""
read -p "Configure supplier API keys? (y/N): " configure_suppliers
supplier_env=""

if [[ "$configure_suppliers" =~ ^[Yy]$ ]]; then
    echo ""
    print_info "Supplier API Configuration (press Enter to skip)"

    read -p "DigiKey Client ID: " digikey_id
    if [ ! -z "$digikey_id" ]; then
        read -p "DigiKey Client Secret: " digikey_secret
        supplier_env="$supplier_env -e DIGIKEY_CLIENT_ID=$digikey_id -e DIGIKEY_CLIENT_SECRET=$digikey_secret"
    fi

    read -p "Mouser API Key: " mouser_key
    if [ ! -z "$mouser_key" ]; then
        supplier_env="$supplier_env -e MOUSER_API_KEY=$mouser_key"
    fi

    read -p "LCSC API Key: " lcsc_key
    if [ ! -z "$lcsc_key" ]; then
        supplier_env="$supplier_env -e LCSC_API_KEY=$lcsc_key"
    fi
fi

# Run the container
echo ""
print_info "Starting MakerMatrix container..."

docker run -d \
  --name "$CONTAINER_NAME" \
  -p "$PORT:8080" \
  -v "$VOLUME_NAME:/data" \
  -e JWT_SECRET_KEY="$jwt_secret" \
  -e ACCESS_TOKEN_EXPIRE_MINUTES=1440 \
  -e DEBUG=false \
  $supplier_env \
  --restart unless-stopped \
  "$FULL_IMAGE"

# Wait for container to be healthy
echo ""
print_info "Waiting for MakerMatrix to start..."
sleep 5

# Check if container is running
if docker ps | grep -q "$CONTAINER_NAME"; then
    print_success "MakerMatrix is running!"
    echo ""
    echo -e "${GREEN}════════════════════════════════════════════${NC}"
    echo -e "${GREEN}  MakerMatrix is now running!${NC}"
    echo -e "${GREEN}════════════════════════════════════════════${NC}"
    echo ""
    echo "  Access at:  ${BLUE}http://localhost:$PORT${NC}"
    echo ""
    echo "  Default credentials:"
    echo "    Username: ${YELLOW}admin${NC}"
    echo "    Password: ${YELLOW}admin123${NC}"
    echo ""
    print_warning "Change the default password after first login!"
    echo ""
    echo "Useful commands:"
    echo "  View logs:   ${BLUE}docker logs -f $CONTAINER_NAME${NC}"
    echo "  Stop:        ${BLUE}docker stop $CONTAINER_NAME${NC}"
    echo "  Restart:     ${BLUE}docker restart $CONTAINER_NAME${NC}"
    echo "  Backup data: ${BLUE}docker run --rm -v $VOLUME_NAME:/data -v \$(pwd):/backup alpine tar czf /backup/makermatrix-backup.tar.gz /data${NC}"
    echo ""
else
    print_error "Container failed to start. Check logs:"
    echo "  docker logs $CONTAINER_NAME"
    exit 1
fi
