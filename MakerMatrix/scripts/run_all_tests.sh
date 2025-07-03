#!/bin/bash

echo "🧪 Running MakerMatrix Test Suite"
echo "================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test results
BACKEND_RESULT=0
FRONTEND_RESULT=0
INTEGRATION_RESULT=0

# Run backend API tests
echo -e "\n${YELLOW}1. Running Backend API CRUD Tests...${NC}"
source venv_test/bin/activate
python test_crud_operations.py
BACKEND_RESULT=$?

# Run frontend unit tests
echo -e "\n${YELLOW}2. Running Frontend Unit Tests...${NC}"
cd MakerMatrix/frontend
npm test -- --run src/__tests__/api/crud.test.ts
FRONTEND_UNIT_RESULT=$?

# Run frontend integration tests
echo -e "\n${YELLOW}3. Running Frontend Integration Tests...${NC}"
npm test -- --run src/__tests__/integration/crud-flow.test.tsx
FRONTEND_INTEGRATION_RESULT=$?

cd ../..

# Calculate overall result
OVERALL_RESULT=$((BACKEND_RESULT + FRONTEND_UNIT_RESULT + FRONTEND_INTEGRATION_RESULT))

# Print summary
echo -e "\n${YELLOW}================================${NC}"
echo -e "${YELLOW}TEST SUMMARY${NC}"
echo -e "${YELLOW}================================${NC}"

if [ $BACKEND_RESULT -eq 0 ]; then
    echo -e "Backend API Tests: ${GREEN}✅ PASSED${NC}"
else
    echo -e "Backend API Tests: ${RED}❌ FAILED${NC}"
fi

if [ $FRONTEND_UNIT_RESULT -eq 0 ]; then
    echo -e "Frontend Unit Tests: ${GREEN}✅ PASSED${NC}"
else
    echo -e "Frontend Unit Tests: ${RED}❌ FAILED${NC}"
fi

if [ $FRONTEND_INTEGRATION_RESULT -eq 0 ]; then
    echo -e "Frontend Integration Tests: ${GREEN}✅ PASSED${NC}"
else
    echo -e "Frontend Integration Tests: ${RED}❌ FAILED${NC}"
fi

echo -e "${YELLOW}================================${NC}"

if [ $OVERALL_RESULT -eq 0 ]; then
    echo -e "${GREEN}✅ ALL TESTS PASSED!${NC}"
    exit 0
else
    echo -e "${RED}❌ SOME TESTS FAILED!${NC}"
    exit 1
fi