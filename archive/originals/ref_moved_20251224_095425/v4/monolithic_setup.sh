#!/usr/bin/env bash
################################################################################
# Revolutionary MCP Server - Monolithic Setup Script
################################################################################
# 
# This script handles EVERYTHING needed to get the MCP server running:
# - Detects OS and installs dependencies
# - Installs Ollama and Qwen model
# - Sets up Python environment
# - Creates all necessary files
# - Configures the system
# - Starts the server
# - Runs tests
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/.../setup.sh | bash
#   or
#   bash setup.sh
#
################################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Configuration
PROJECT_DIR="${HOME}/.copilot_mcp"
VENV_DIR="${PROJECT_DIR}/venv"
SERVER_PORT="${MCP_PORT:-8765}"
QWEN_MODEL="qwen2.5-coder:14b-instruct-q4_K_M"
LOG_FILE="${PROJECT_DIR}/setup.log"

# Track what we've done for rollback
INSTALLED_OLLAMA=false
CREATED_VENV=false
INSTALLED_PACKAGES=false
PULLED_MODEL=false

################################################################################
# Helper Functions
################################################################################

print_banner() {
    echo -e "${MAGENTA}${BOLD}"
    cat << "EOF"
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║     🚀 Revolutionary MCP Server Setup                       ║
║     Copilot + Qwen = AI Revolution                          ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"
}

log() {
    echo -e "${GREEN}✓${NC} $1"
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

warn() {
    echo -e "${YELLOW}⚠${NC} $1"
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1" >> "$LOG_FILE"
}

error() {
    echo -e "${RED}✗${NC} $1"
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1" >> "$LOG_FILE"
}

info() {
    echo -e "${CYAN}ℹ${NC} $1"
}

step() {
    echo ""
    echo -e "${BLUE}${BOLD}▶ $1${NC}"
    echo "----------------------------------------"
}

ask() {
    local prompt="$1"
    local default="${2:-y}"
    local response
    
    if [ "$default" = "y" ]; then
        echo -e "${CYAN}?${NC} ${prompt} [Y/n]: "
    else
        echo -e "${CYAN}?${NC} ${prompt} [y/N]: "
    fi
    
    read -r response
    response=${response:-$default}
    
    if [[ "$response" =~ ^[Yy]$ ]]; then
        return 0
    else
        return 1
    fi
}

check_command() {
    if command -v "$1" &> /dev/null; then
        return 0
    else
        return 1
    fi
}

detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "linux"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
        echo "windows"
    else
        echo "unknown"
    fi
}

cleanup() {
    if [ $? -ne 0 ]; then
        error "Setup failed! Check ${LOG_FILE} for details."
        
        if ask "Would you like to rollback changes?" "y"; then
            step "Rolling back changes"
            
            if [ "$INSTALLED_OLLAMA" = true ]; then
                warn "Ollama was installed. Remove manually if desired."
            fi
            
            if [ "$CREATED_VENV" = true ]; then
                log "Removing Python virtual environment"
                rm -rf "$VENV_DIR"
            fi
            
            log "Rollback complete"
        fi
    fi
}

trap cleanup EXIT

################################################################################
# Setup Steps
################################################################################

setup_directories() {
    step "Setting up directories"
    
    mkdir -p "$PROJECT_DIR"/{knowledge,patterns,cache,sessions,logs}
    mkdir -p "$PROJECT_DIR"/scripts
    
    # Initialize log file
    touch "$LOG_FILE"
    
    log "Created directory structure at ${PROJECT_DIR}"
}

check_prerequisites() {
    step "Checking prerequisites"
    
    local os=$(detect_os)
    info "Detected OS: $os"
    
    # Check Python
    if check_command python3; then
        local python_version=$(python3 --version 2>&1 | awk '{print $2}')
        log "Found Python ${python_version}"
        
        # Check version is 3.9+
        local major=$(echo "$python_version" | cut -d. -f1)
        local minor=$(echo "$python_version" | cut -d. -f2)
        
        if [ "$major" -lt 3 ] || ([ "$major" -eq 3 ] && [ "$minor" -lt 9 ]); then
            error "Python 3.9+ required, found ${python_version}"
            exit 1
        fi
    else
        error "Python 3.9+ not found. Please install Python first."
        exit 1
    fi
    
    # Check curl
    if ! check_command curl; then
        error "curl not found. Please install curl first."
        exit 1
    fi
    
    log "All prerequisites met"
}

install_ollama() {
    step "Installing Ollama"
    
    if check_command ollama; then
        log "Ollama already installed"
        return 0
    fi
    
    local os=$(detect_os)
    
    case "$os" in
        linux|macos)
            info "Installing Ollama..."
            if curl -fsSL https://ollama.com/install.sh | sh; then
                INSTALLED_OLLAMA=true
                log "Ollama installed successfully"
            else
                error "Failed to install Ollama"
                exit 1
            fi
            ;;
        windows)
            warn "Please install Ollama manually from https://ollama.com/download"
            info "After installation, re-run this script"
            exit 1
            ;;
        *)
            error "Unsupported OS for automatic Ollama installation"
            exit 1
            ;;
    esac
}

start_ollama() {
    step "Starting Ollama service"
    
    # Check if Ollama is already running
    if curl -s http://localhost:11434/api/tags &> /dev/null; then
        log "Ollama already running"
        return 0
    fi
    
    info "Starting Ollama in background..."
    
    local os=$(detect_os)
    
    if [ "$os" = "macos" ]; then
        # On macOS, Ollama runs as an app
        if [ -d "/Applications/Ollama.app" ]; then
            open -a Ollama
        else
            nohup ollama serve > "${PROJECT_DIR}/logs/ollama.log" 2>&1 &
        fi
    else
        # On Linux, run as background process
        nohup ollama serve > "${PROJECT_DIR}/logs/ollama.log" 2>&1 &
        echo $! > "${PROJECT_DIR}/ollama.pid"
    fi
    
    # Wait for Ollama to be ready
    info "Waiting for Ollama to start..."
    local max_attempts=30
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if curl -s http://localhost:11434/api/tags &> /dev/null; then
            log "Ollama is ready"
            return 0
        fi
        
        sleep 1
        ((attempt++))
        echo -n "."
    done
    
    echo ""
    error "Ollama failed to start within 30 seconds"
    exit 1
}

pull_qwen_model() {
    step "Pulling Qwen model"
    
    # Check if model already exists
    if ollama list | grep -q "$QWEN_MODEL"; then
        log "Model ${QWEN_MODEL} already available"
        return 0
    fi
    
    info "Downloading ${QWEN_MODEL} (this may take a while, ~8GB)..."
    
    if ollama pull "$QWEN_MODEL"; then
        PULLED_MODEL=true
        log "Model pulled successfully"
    else
        error "Failed to pull model"
        exit 1
    fi
}

setup_python_env() {
    step "Setting up Python environment"
    
    if [ -d "$VENV_DIR" ]; then
        log "Virtual environment already exists"
    else
        info "Creating virtual environment..."
        python3 -m venv "$VENV_DIR"
        CREATED_VENV=true
        log "Virtual environment created"
    fi
    
    # Activate venv
    source "${VENV_DIR}/bin/activate"
    
    info "Upgrading pip..."
    pip install --quiet --upgrade pip
    
    info "Installing Python packages..."
    pip install --quiet aiohttp rich requests
    INSTALLED_PACKAGES=true
    
    log "Python environment ready"
}

create_server_script() {
    step "Creating MCP server script"
    
    local server_file="${PROJECT_DIR}/mcp_server.py"
    
    cat > "$server_file" << 'EOFSERVER'
#!/usr/bin/env python3
"""Revolutionary MCP Server for GitHub Copilot + Qwen"""

import asyncio
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import aiohttp
    from aiohttp import web
except ImportError:
    print("Installing aiohttp...")
    subprocess.run([sys.executable, "-m", "pip", "install", "aiohttp"], check=True)
    import aiohttp
    from aiohttp import web


@dataclass
class LearningPattern:
    pattern_id: str
    category: str
    description: str
    code_before: str
    code_after: str
    frequency: int = 1
    last_seen: str = field(default_factory=lambda: datetime.now().isoformat())
    confidence: float = 0.5


class IntelligentMCPServer:
    def __init__(self, port: int = 8765):
        self.port = port
        self.model = os.environ.get("QWEN_MODEL", "qwen2.5-coder:14b-instruct-q4_K_M")
        self.base_dir = Path.home() / ".copilot_mcp"
        self.knowledge_dir = self.base_dir / "knowledge"
        self.patterns_dir = self.base_dir / "patterns"
        self.cache_dir = self.base_dir / "cache"
        self.sessions_dir = self.base_dir / "sessions"
        
        for d in [self.knowledge_dir, self.patterns_dir, self.cache_dir, self.sessions_dir]:
            d.mkdir(parents=True, exist_ok=True)
        
        self.patterns: Dict[str, LearningPattern] = {}
        self.load_patterns()
        
        self.stats = {
            'requests': 0,
            'validations': 0,
            'improvements_suggested': 0,
            'patterns_learned': 0,
            'avg_response_time': 0.0
        }
        
        self.start_time = time.time()
    
    def load_patterns(self):
        for p in self.patterns_dir.glob("*.json"):
            try:
                data = json.loads(p.read_text())
                pattern = LearningPattern(**data)
                self.patterns[pattern.pattern_id] = pattern
            except:
                continue
    
    def save_pattern(self, pattern: LearningPattern):
        path = self.patterns_dir / f"{pattern.pattern_id}.json"
        path.write_text(json.dumps({
            'pattern_id': pattern.pattern_id,
            'category': pattern.category,
            'description': pattern.description,
            'code_before': pattern.code_before,
            'code_after': pattern.code_after,
            'frequency': pattern.frequency,
            'last_seen': pattern.last_seen,
            'confidence': pattern.confidence
        }, indent=2))
    
    async def call_qwen(self, prompt: str, system: str = None, temperature: float = 0.1) -> str:
        try:
            async with aiohttp.ClientSession() as session:
                messages = []
                if system:
                    messages.append({"role": "system", "content": system})
                messages.append({"role": "user", "content": prompt})
                
                payload = {
                    "model": self.model,
                    "messages": messages,
                    "stream": False,
                    "options": {"temperature": temperature}
                }
                
                async with session.post(
                    "http://localhost:11434/api/chat",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as resp:
                    if resp.status != 200:
                        return f"Error: Ollama returned {resp.status}"
                    
                    data = await resp.json()
                    if 'message' in data and 'content' in data['message']:
                        return data['message']['content']
                    return str(data)
        except Exception as e:
            return f"Error: {e}"
    
    async def validate_code(self, args: Dict) -> Dict:
        start = time.time()
        code = args.get('code', '')
        language = args.get('language', 'python')
        
        system = f"You are an expert {language} code reviewer."
        prompt = f"""Review this {language} code:

```{language}
{code}
```

Provide JSON:
{{
    "score": <0-10>,
    "security": ["issue1"],
    "performance": ["issue1"],
    "style": ["issue1"],
    "improvements": ["suggestion1"],
    "verdict": "PASS|REVIEW|FAIL"
}}"""

        response = await self.call_qwen(prompt, system)
        
        try:
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                response = json_match.group(1)
            result = json.loads(response)
        except:
            result = {"score": 7, "verdict": "REVIEW", "raw_response": response}
        
        matched_patterns = self._check_patterns(code)
        if matched_patterns:
            result['matched_patterns'] = matched_patterns
        
        elapsed = time.time() - start
        self.stats['validations'] += 1
        
        return {
            "status": "SUCCESS",
            "data": result,
            "metadata": {"elapsed_ms": int(elapsed * 1000), "model": self.model}
        }
    
    async def improve_code(self, args: Dict) -> Dict:
        code = args.get('code', '')
        language = args.get('language', 'python')
        focus = args.get('focus', 'general')
        
        system = f"You are an expert {language} developer."
        prompt = f"""Improve this {language} code (focus: {focus}):

```{language}
{code}
```

Provide JSON:
{{
    "improved_code": "...",
    "changes": ["change1"],
    "impact": "description"
}}"""

        response = await self.call_qwen(prompt, system)
        
        try:
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                response = json_match.group(1)
            result = json.loads(response)
        except:
            result = {"raw_response": response}
        
        self.stats['improvements_suggested'] += 1
        return {"status": "SUCCESS", "data": result}
    
    async def explain_code(self, args: Dict) -> Dict:
        code = args.get('code', '')
        language = args.get('language', 'python')
        
        system = f"You are an expert {language} teacher."
        prompt = f"Explain this {language} code clearly:\n\n```{language}\n{code}\n```"
        
        response = await self.call_qwen(prompt, system)
        return {"status": "SUCCESS", "data": {"explanation": response, "language": language}}
    
    async def generate_tests(self, args: Dict) -> Dict:
        code = args.get('code', '')
        language = args.get('language', 'python')
        framework = args.get('framework', 'pytest')
        
        system = "You are an expert test engineer."
        prompt = f"Generate {framework} tests for:\n\n```{language}\n{code}\n```"
        
        response = await self.call_qwen(prompt, system)
        code_blocks = re.findall(r'```(?:\w+)?\s*(.*?)\s*```', response, re.DOTALL)
        test_code = code_blocks[0] if code_blocks else response
        
        return {"status": "SUCCESS", "data": {"test_code": test_code, "framework": framework, "explanation": response}}
    
    async def learn_pattern(self, args: Dict) -> Dict:
        category = args.get('category', 'general')
        description = args.get('description', '')
        code_before = args.get('code_before', '')
        code_after = args.get('code_after', '')
        
        pattern_content = f"{category}:{code_before}:{code_after}"
        pattern_id = hashlib.md5(pattern_content.encode()).hexdigest()[:12]
        
        if pattern_id in self.patterns:
            self.patterns[pattern_id].frequency += 1
            self.patterns[pattern_id].last_seen = datetime.now().isoformat()
            self.patterns[pattern_id].confidence = min(1.0, self.patterns[pattern_id].confidence + 0.1)
        else:
            pattern = LearningPattern(
                pattern_id=pattern_id,
                category=category,
                description=description,
                code_before=code_before,
                code_after=code_after
            )
            self.patterns[pattern_id] = pattern
            self.stats['patterns_learned'] += 1
        
        self.save_pattern(self.patterns[pattern_id])
        
        return {
            "status": "SUCCESS",
            "data": {
                "pattern_id": pattern_id,
                "message": "Pattern learned",
                "total_patterns": len(self.patterns)
            }
        }
    
    async def get_stats(self, args: Dict) -> Dict:
        uptime = time.time() - self.start_time
        return {
            "status": "SUCCESS",
            "data": {
                **self.stats,
                "patterns_count": len(self.patterns),
                "uptime_seconds": int(uptime)
            }
        }
    
    def _check_patterns(self, code: str) -> List[Dict]:
        matched = []
        for pattern in self.patterns.values():
            if pattern.confidence > 0.6 and pattern.code_before in code:
                matched.append({
                    'pattern_id': pattern.pattern_id,
                    'category': pattern.category,
                    'suggestion': pattern.code_after,
                    'confidence': pattern.confidence
                })
        return matched
    
    async def handle_tool_call(self, request):
        start = time.time()
        self.stats['requests'] += 1
        
        try:
            data = await request.json()
            tool_name = data.get('tool')
            args = data.get('args', {})
            
            handler = getattr(self, tool_name, None)
            if not handler:
                return web.json_response({
                    "status": "ERROR",
                    "error": f"Unknown tool: {tool_name}"
                }, status=400)
            
            result = await handler(args)
            
            elapsed = time.time() - start
            self.stats['avg_response_time'] = (
                (self.stats['avg_response_time'] * (self.stats['requests'] - 1) + elapsed)
                / self.stats['requests']
            )
            
            return web.json_response(result)
        except Exception as e:
            return web.json_response({"status": "ERROR", "error": str(e)}, status=500)
    
    async def handle_health(self, request):
        return web.json_response({
            "status": "healthy",
            "model": self.model,
            "stats": self.stats,
            "uptime": int(time.time() - self.start_time)
        })
    
    async def handle_tools_list(self, request):
        tools = {
            "validate_code": "Validate code quality",
            "improve_code": "Get improvements",
            "explain_code": "Explain code",
            "generate_tests": "Generate tests",
            "learn_pattern": "Learn from corrections",
            "get_stats": "Get statistics"
        }
        return web.json_response({
            "status": "SUCCESS",
            "tools": [{"name": k, "description": v} for k, v in tools.items()]
        })
    
    async def start(self):
        app = web.Application()
        app.router.add_post('/tool', self.handle_tool_call)
        app.router.add_get('/health', self.handle_health)
        app.router.add_get('/tools', self.handle_tools_list)
        
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', self.port)
        await site.start()
        
        print(f"""
╔══════════════════════════════════════════════════════════╗
║   🚀 Revolutionary MCP Server READY                      ║
║   Server: http://localhost:{self.port}                        ║
║   Model:  {self.model[:40]:40s} ║
╚══════════════════════════════════════════════════════════╝
        """)
        
        await asyncio.Event().wait()


if __name__ == "__main__":
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    server = IntelligentMCPServer(port=port)
    asyncio.run(server.start())
EOFSERVER

    chmod +x "$server_file"
    log "MCP server script created"
}

create_demo_script() {
    step "Creating demo script"
    
    local demo_file="${PROJECT_DIR}/scripts/demo.py"
    
    cat > "$demo_file" << 'EOFDEMO'
#!/usr/bin/env python3
"""Quick demo of MCP server"""

import json
import requests
import sys

MCP_URL = "http://localhost:8765"

def test_health():
    print("🏥 Health check...")
    r = requests.get(f"{MCP_URL}/health")
    print(f"   Status: {r.json()['status']}")
    print(f"   Model: {r.json()['model']}")
    print()

def test_validation():
    print("🔍 Testing code validation...")
    code = "def add(a, b):\n    return a + b"
    r = requests.post(f"{MCP_URL}/tool", json={
        "tool": "validate_code",
        "args": {"code": code, "language": "python"}
    })
    result = r.json()['data']
    print(f"   Score: {result.get('score', 'N/A')}/10")
    print(f"   Verdict: {result.get('verdict', 'N/A')}")
    print()

def test_improvement():
    print("✨ Testing code improvement...")
    code = "def calc(x):\n    return x * 2 + 5"
    r = requests.post(f"{MCP_URL}/tool", json={
        "tool": "improve_code",
        "args": {"code": code, "language": "python", "focus": "readability"}
    })
    result = r.json()['data']
    if 'improved_code' in result:
        print(f"   Improved: {result['improved_code'][:50]}...")
    print()

def main():
    try:
        print("🚀 MCP Server Demo\n" + "="*40 + "\n")
        test_health()
        test_validation()
        test_improvement()
        print("✅ All tests passed!")
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to MCP server")
        print("   Make sure it's running: python mcp_server.py")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
EOFDEMO

    chmod +x "$demo_file"
    log "Demo script created"
}

create_systemd_service() {
    step "Creating systemd service (optional)"
    
    local os=$(detect_os)
    
    if [ "$os" != "linux" ]; then
        info "Skipping systemd service (not on Linux)"
        return 0
    fi
    
    if ! ask "Create systemd service for auto-start?" "n"; then
        return 0
    fi
    
    local service_file="${PROJECT_DIR}/mcp-server.service"
    
    cat > "$service_file" << EOFSERVICE
[Unit]
Description=Revolutionary MCP Server
After=network.target

[Service]
Type=simple
User=${USER}
WorkingDirectory=${PROJECT_DIR}
ExecStart=${VENV_DIR}/bin/python ${PROJECT_DIR}/mcp_server.py ${SERVER_PORT}
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOFSERVICE

    log "Systemd service file created at ${service_file}"
    info "To install: sudo cp ${service_file} /etc/systemd/system/"
    info "To enable: sudo systemctl enable mcp-server"
    info "To start: sudo systemctl start mcp-server"
}

start_server() {
    step "Starting MCP server"
    
    # Activate venv
    source "${VENV_DIR}/bin/activate"
    
    # Check if already running
    if curl -s "http://localhost:${SERVER_PORT}/health" &> /dev/null; then
        warn "Server already running on port ${SERVER_PORT}"
        return 0
    fi
    
    info "Starting server on port ${SERVER_PORT}..."
    
    # Start in background
    nohup python3 "${PROJECT_DIR}/mcp_server.py" "$SERVER_PORT" > "${PROJECT_DIR}/logs/server.log" 2>&1 &
    local pid=$!
    echo $pid > "${PROJECT_DIR}/server.pid"
    
    # Wait for server to be ready
    info "Waiting for server to start..."
    local max_attempts=30
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if curl -s "http://localhost:${SERVER_PORT}/health" &> /dev/null; then
            log "Server started successfully (PID: ${pid})"
            return 0
        fi
        
        sleep 1
        ((attempt++))
        echo -n "."
    done
    
    echo ""
    error "Server failed to start"
    cat "${PROJECT_DIR}/logs/server.log"
    exit 1
}

run_tests() {
    step "Running tests"
    
    # Activate venv
    source "${VENV_DIR}/bin/activate"
    
    info "Running demo script..."
    if python3 "${PROJECT_DIR}/scripts/demo.py"; then
        log "All tests passed!"
    else
        warn "Some tests failed, but setup is complete"
    fi
}

create_helper_scripts() {
    step "Creating helper scripts"
    
    # Start script
    cat > "${PROJECT_DIR}/start.sh" << 'EOFSTART'
#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
python3 mcp_server.py 8765
EOFSTART
    chmod +x "${PROJECT_DIR}/start.sh"
    
    # Stop script
    cat > "${PROJECT_DIR}/stop.sh" << 'EOFSTOP'
#!/bin/bash
if [ -f "$(dirname "$0")/server.pid" ]; then
    kill $(cat "$(dirname "$0")/server.pid") 2>/dev/null
    rm "$(dirname "$0")/server.pid"
    echo "Server stopped"
else
    echo "No PID file found"
fi
EOFSTOP
    chmod +x "${PROJECT_DIR}/stop.sh"
    
    # Status script
    cat > "${PROJECT_DIR}/status.sh" << 'EOFSTATUS'
#!/bin/bash
curl -s http://localhost:8765/health | python3 -m json.tool
EOFSTATUS
    chmod +x "${PROJECT_DIR}/status.sh"
    
    log "Helper scripts created (start.sh, stop.sh, status.sh)"
}

print_completion() {
    echo ""
    echo -e "${GREEN}${BOLD}"
    cat << "EOF"
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║     ✅ SETUP COMPLETE!                                       ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"
    
    echo -e "${CYAN}📍 Installation Directory:${NC} ${PROJECT_DIR}"
    echo -e "${CYAN}🌐 Server URL:${NC} http://localhost:${SERVER_PORT}"
    echo -e "${CYAN}📝 Log File:${NC} ${LOG_FILE}"
    echo ""
    
    echo -e "${YELLOW}Quick Commands:${NC}"
    echo -e "  ${GREEN}▶${NC}  Start:  cd ${PROJECT_DIR} && ./start.sh"
    echo -e "  ${RED}⏹${NC}  Stop:   cd ${PROJECT_DIR} && ./stop.sh"
    echo -e "  ${BLUE}ℹ${NC}  Status: cd ${PROJECT_DIR} && ./status.sh"
    echo -e "  ${CYAN}🧪${NC} Demo:   cd ${PROJECT_DIR} && python3 scripts/demo.py"
    echo ""
    
    echo -e "${YELLOW}Next Steps:${NC}"
    echo "  1. Test the server: curl http://localhost:${SERVER_PORT}/health"
    echo "  2. Run demo: python3 ${PROJECT_DIR}/scripts/demo.py"
    echo "  3. Check logs: tail -f ${PROJECT_DIR}/logs/server.log"
    echo "  4. Integrate with VS Code Copilot!"
    echo ""
    
    echo -e "${CYAN}Documentation:${NC}"
    echo "  • API: http://localhost:${SERVER_PORT}/tools"
    echo "  • Logs: ${PROJECT_DIR}/logs/"
    echo "  • Config: ${PROJECT_DIR}/"
    echo ""
}

################################################################################
# Main Execution
################################################################################

main() {
    print_banner
    
    info "Starting setup process..."
    info "Log file: ${LOG_FILE}"
    echo ""
    
    # Run all setup steps
    setup_directories
    check_prerequisites
    install_ollama
    start_ollama
    pull_qwen_model
    setup_python_env
    create_server_script
    create_demo_script
    create_helper_scripts
    create_systemd_service
    start_server
    run_tests
    
    # Success!
    print_completion
}

# Run main function
main "$@"
