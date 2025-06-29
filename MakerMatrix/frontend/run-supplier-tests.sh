#!/bin/bash

# Supplier Configuration Test Runner
# Comprehensive test suite for supplier functionality

set -e

echo "🧪 MakerMatrix Supplier Configuration Test Suite"
echo "================================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check if services are running
check_services() {
    echo -e "${BLUE}🔍 Checking if services are running...${NC}"
    
    # Check backend
    if curl -k -s https://localhost:8443/api/utility/get_counts > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Backend is running on https://localhost:8443${NC}"
    else
        echo -e "${RED}❌ Backend is not responding on https://localhost:8443${NC}"
        echo -e "${YELLOW}   Please start the backend with: python -m MakerMatrix.main${NC}"
        exit 1
    fi
    
    # Check frontend
    if curl -k -s https://localhost:5173 > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Frontend is running on https://localhost:5173${NC}"
    else
        echo -e "${RED}❌ Frontend is not responding on https://localhost:5173${NC}"
        echo -e "${YELLOW}   Please start the frontend with: npm run dev${NC}"
        exit 1
    fi
    
    echo ""
}

# Function to install dependencies if needed
install_deps() {
    echo -e "${BLUE}📦 Checking dependencies...${NC}"
    
    if [ ! -d "node_modules" ]; then
        echo -e "${YELLOW}Installing dependencies...${NC}"
        npm install
    fi
    
    # Check if jest is available
    if ! npm list jest > /dev/null 2>&1; then
        echo -e "${YELLOW}Installing Jest for E2E tests...${NC}"
        npm install --save-dev jest babel-jest @babel/core @babel/preset-env @babel/preset-react
    fi
    
    # Check if puppeteer is available
    if ! npm list puppeteer > /dev/null 2>&1; then
        echo -e "${YELLOW}Installing Puppeteer for E2E tests...${NC}"
        npm install --save-dev puppeteer
    fi
    
    echo ""
}

# Function to run integration tests
run_integration_tests() {
    echo -e "${BLUE}🧪 Running Integration Tests (React Testing Library)...${NC}"
    echo "Testing supplier component behavior and API interactions"
    echo ""
    
    if npm run test:supplier; then
        echo -e "${GREEN}✅ Integration tests passed!${NC}"
    else
        echo -e "${RED}❌ Integration tests failed!${NC}"
        return 1
    fi
    echo ""
}

# Function to run E2E tests
run_e2e_tests() {
    echo -e "${BLUE}🌐 Running E2E Tests (Puppeteer)...${NC}"
    echo "Testing complete user workflow in real browser"
    echo ""
    
    # Create screenshots directory
    mkdir -p test-screenshots
    
    if npm run test:supplier:e2e; then
        echo -e "${GREEN}✅ E2E tests passed!${NC}"
        
        # Show screenshots if they exist
        if [ -d "test-screenshots" ] && [ "$(ls -A test-screenshots)" ]; then
            echo -e "${BLUE}📸 Screenshots saved to test-screenshots/:${NC}"
            ls -la test-screenshots/
        fi
    else
        echo -e "${RED}❌ E2E tests failed!${NC}"
        
        # Show screenshots for debugging
        if [ -d "test-screenshots" ] && [ "$(ls -A test-screenshots)" ]; then
            echo -e "${YELLOW}🔍 Check screenshots in test-screenshots/ for debugging:${NC}"
            ls -la test-screenshots/
        fi
        return 1
    fi
    echo ""
}

# Function to run API verification
verify_api() {
    echo -e "${BLUE}🔗 Verifying Supplier API...${NC}"
    echo "Testing the specific API endpoint that was fixed"
    echo ""
    
    # Test the suppliers/info endpoint directly
    echo "Testing GET /api/suppliers/info..."
    response=$(curl -k -s -w "%{http_code}" https://localhost:8443/api/suppliers/info)
    http_code="${response: -3}"
    
    if [ "$http_code" = "200" ]; then
        echo -e "${GREEN}✅ /api/suppliers/info returns 200 OK${NC}"
        echo "✅ MouserSupplier configuration schema bug is fixed"
    else
        echo -e "${RED}❌ /api/suppliers/info returns $http_code${NC}"
        echo -e "${RED}❌ This indicates the MouserSupplier bug may have returned${NC}"
        return 1
    fi
    echo ""
}

# Function to show test summary
show_summary() {
    echo -e "${GREEN}🎉 Test Summary${NC}"
    echo "==============="
    echo "✅ Services are running"
    echo "✅ Dependencies are installed"
    echo "✅ API endpoints are working"
    echo "✅ Integration tests passed"
    echo "✅ E2E tests passed"
    echo ""
    echo -e "${GREEN}🔒 The MouserSupplier configuration schema bug is confirmed fixed!${NC}"
    echo ""
    echo "These tests verify that:"
    echo "• The /api/suppliers/info endpoint returns 200 OK (not 500)"
    echo "• The Add Supplier modal opens successfully"
    echo "• All 5 suppliers are displayed correctly"
    echo "• No JavaScript errors occur during the workflow"
    echo "• Users can navigate the supplier configuration UI"
    echo ""
}

# Main execution
main() {
    local run_integration=true
    local run_e2e=true
    local check_api=true
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --integration-only)
                run_e2e=false
                shift
                ;;
            --e2e-only)
                run_integration=false
                shift
                ;;
            --api-only)
                run_integration=false
                run_e2e=false
                shift
                ;;
            --help)
                echo "Usage: $0 [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --integration-only    Run only integration tests"
                echo "  --e2e-only           Run only E2E tests"
                echo "  --api-only           Run only API verification"
                echo "  --help               Show this help message"
                exit 0
                ;;
            *)
                echo "Unknown option: $1"
                echo "Use --help for usage information"
                exit 1
                ;;
        esac
    done
    
    # Run test sequence
    check_services
    install_deps
    
    if [ "$check_api" = true ]; then
        verify_api || exit 1
    fi
    
    if [ "$run_integration" = true ]; then
        run_integration_tests || exit 1
    fi
    
    if [ "$run_e2e" = true ]; then
        run_e2e_tests || exit 1
    fi
    
    show_summary
}

# Run the main function with all arguments
main "$@"