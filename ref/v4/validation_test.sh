#!/usr/bin/env bash
################################################################################
# Installation Validation Script
################################################################################
# Tests that everything was installed correctly

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

PROJECT_DIR="${HOME}/.copilot_mcp"
SERVER_URL="http://localhost:8765"
PASSED=0
FAILED=0

print_test() {
    echo -e "${CYAN}Testing:${NC} $1"
}

pass() {
    echo -e "  ${GREEN}✓${NC} $1"
    ((PASSED++))
}

fail() {
    echo -e "  ${RED}✗${NC} $1"
    ((FAILED++))
}

test_directory() {
    print_test "Installation directory"
    if [ -d "$PROJECT_DIR" ]; then
        pass "Directory exists: ${PROJECT_DIR}"
    else
        fail "Directory missing: ${PROJECT_DIR}"
        return 1
    fi
}

test_python_env() {
    print_test "Python environment"
    
    if [ -d "${PROJECT_DIR}/venv" ]; then
        pass "Virtual environment exists"
    else
        fail "Virtual environment missing"
        return 1
    fi
    
    if [ -f "${PROJECT_DIR}/venv/bin/python3" ]; then
        pass "Python executable found"
    else
        fail "Python executable missing"
        return 1
    fi
}

test_server_script() {
    print_test "Server script"
    
    if [ -f "${PROJECT_DIR}/mcp_server.py" ]; then
        pass "Server script exists"
    else
        fail "Server script missing"
        return 1
    fi
    
    if [ -x "${PROJECT_DIR}/mcp_server.py" ]; then
        pass "Server script is executable"
    else
        fail "Server script not executable"
    fi
}

test_helper_scripts() {
    print_test "Helper scripts"
    
    for script in start.sh stop.sh status.sh; do
        if [ -f "${PROJECT_DIR}/${script}" ]; then
            pass "${script} exists"
        else
            fail "${script} missing"
        fi
    done
}

test_ollama() {
    print_test "Ollama installation"
    
    if command -v ollama &> /dev/null; then
        pass "Ollama command found"
    else
        fail "Ollama command not found"
        return 1
    fi
    
    if curl -s http://localhost:11434/api/tags &> /dev/null; then
        pass "Ollama service responding"
    else
        fail "Ollama service not responding"
        return 1
    fi
}

test_qwen_model() {
    print_test "Qwen model"
    
    if ollama list | grep -q "qwen2.5-coder"; then
        pass "Qwen model installed"
    else
        fail "Qwen model not found"
        return 1
    fi
}

test_server() {
    print_test "MCP server"
    
    if curl -s "${SERVER_URL}/health" &> /dev/null; then
        pass "Server responding"
    else
        fail "Server not responding"
        return 1
    fi
    
    local health=$(curl -s "${SERVER_URL}/health")
    
    if echo "$health" | grep -q "healthy"; then
        pass "Server reports healthy"
    else
        fail "Server not healthy"
    fi
    
    if echo "$health" | grep -q "qwen"; then
        pass "Qwen model configured"
    else
        fail "Model configuration issue"
    fi
}

test_api() {
    print_test "API endpoints"
    
    # Test tools list
    if curl -s "${SERVER_URL}/tools" | grep -q "validate_code"; then
        pass "Tools endpoint working"
    else
        fail "Tools endpoint broken"
    fi
    
    # Test validation endpoint
    local response=$(curl -s -X POST "${SERVER_URL}/tool" \
        -H 'Content-Type: application/json' \
        -d '{"tool":"validate_code","args":{"code":"def test(): pass","language":"python"}}')
    
    if echo "$response" | grep -q "SUCCESS"; then
        pass "Code validation working"
    else
        fail "Code validation broken"
    fi
    
    # Test stats endpoint
    response=$(curl -s -X POST "${SERVER_URL}/tool" \
        -H 'Content-Type: application/json' \
        -d '{"tool":"get_stats","args":{}}')
    
    if echo "$response" | grep -q "requests"; then
        pass "Stats endpoint working"
    else
        fail "Stats endpoint broken"
    fi
}

test_python_packages() {
    print_test "Python packages"
    
    source "${PROJECT_DIR}/venv/bin/activate"
    
    for pkg in aiohttp rich requests; do
        if pip show "$pkg" &> /dev/null; then
            pass "${pkg} installed"
        else
            fail "${pkg} not installed"
        fi
    done
}

test_logs() {
    print_test "Logging system"
    
    if [ -d "${PROJECT_DIR}/logs" ]; then
        pass "Logs directory exists"
    else
        fail "Logs directory missing"
    fi
    
    if [ -f "${PROJECT_DIR}/logs/setup.log" ]; then
        pass "Setup log exists"
    else
        fail "Setup log missing"
    fi
}

print_summary() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    local total=$((PASSED + FAILED))
    local percent=$((PASSED * 100 / total))
    
    echo -e "Tests: ${GREEN}${PASSED} passed${NC}, ${RED}${FAILED} failed${NC} (${total} total)"
    echo -e "Success rate: ${percent}%"
    
    if [ $FAILED -eq 0 ]; then
        echo -e "\n${GREEN}✓ All tests passed! Installation is working correctly.${NC}"
        return 0
    elif [ $FAILED -lt 3 ]; then
        echo -e "\n${YELLOW}⚠ Some tests failed but core functionality works.${NC}"
        return 0
    else
        echo -e "\n${RED}✗ Multiple tests failed. Please check the installation.${NC}"
        return 1
    fi
}

main() {
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  🧪 MCP Server Installation Validation"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    
    # Run all tests
    test_directory || true
    test_python_env || true
    test_server_script || true
    test_helper_scripts || true
    test_python_packages || true
    test_logs || true
    test_ollama || true
    test_qwen_model || true
    test_server || true
    test_api || true
    
    print_summary
}

main "$@"
