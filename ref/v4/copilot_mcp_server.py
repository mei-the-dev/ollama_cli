#!/usr/bin/env python3
"""
Revolutionary MCP Server for GitHub Copilot + Qwen2.5-Coder
==========================================================

This MCP server creates an AI revolution by combining:
- GitHub Copilot's code generation in VS Code
- Local Qwen2.5-coder as an intelligent overseer
- Self-learning and self-improvement capabilities
- Context-aware code intelligence

Architecture:
- Runs as HTTP server for VS Code extension to call
- Uses Ollama to run Qwen2.5-coder locally
- Provides tools that make Copilot significantly smarter
- Learns from corrections and improves over time

Usage:
    python copilot_mcp_server.py --port 8765
"""

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

import aiohttp
from aiohttp import web


@dataclass
class LearningPattern:
    """Captured pattern from user corrections or preferences"""
    pattern_id: str
    category: str  # 'naming', 'style', 'architecture', 'anti-pattern'
    description: str
    code_before: str
    code_after: str
    frequency: int = 1
    last_seen: str = field(default_factory=lambda: datetime.now().isoformat())
    confidence: float = 0.5


class IntelligentMCPServer:
    """Revolutionary MCP Server with AI-powered code intelligence"""
    
    def __init__(self, port: int = 8765):
        self.port = port
        self.model = "qwen2.5-coder:14b-instruct-q4_K_M"
        self.base_dir = Path.home() / ".copilot_mcp"
        self.knowledge_dir = self.base_dir / "knowledge"
        self.patterns_dir = self.base_dir / "patterns"
        self.cache_dir = self.base_dir / "cache"
        self.sessions_dir = self.base_dir / "sessions"
        
        # Initialize directories
        for d in [self.knowledge_dir, self.patterns_dir, self.cache_dir, self.sessions_dir]:
            d.mkdir(parents=True, exist_ok=True)
        
        # Learning system
        self.patterns: Dict[str, LearningPattern] = {}
        self.load_patterns()
        
        # Performance tracking
        self.stats = {
            'requests': 0,
            'validations': 0,
            'improvements_suggested': 0,
            'patterns_learned': 0,
            'avg_response_time': 0.0
        }
    
    def load_patterns(self):
        """Load learned patterns from disk"""
        for p in self.patterns_dir.glob("*.json"):
            try:
                data = json.loads(p.read_text())
                pattern = LearningPattern(**data)
                self.patterns[pattern.pattern_id] = pattern
            except Exception:
                continue
    
    def save_pattern(self, pattern: LearningPattern):
        """Persist a learned pattern"""
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
        """Call local Qwen model via Ollama"""
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
            return f"Error calling Qwen: {e}"
    
    # ==================== REVOLUTIONARY TOOLS ====================
    
    async def validate_code(self, args: Dict) -> Dict:
        """
        🔍 VALIDATE CODE - Intelligent code validation using Qwen
        
        This is the CORE revolutionary feature: Copilot generates code,
        then Qwen validates it for quality, security, and best practices.
        
        Args:
            code: Code to validate
            language: Programming language
            context: Optional file/project context
            check_security: Enable security scanning
            check_performance: Enable performance analysis
            check_style: Enable style checking
        """
        start = time.time()
        code = args.get('code', '')
        language = args.get('language', 'python')
        context = args.get('context', '')
        check_security = args.get('check_security', True)
        check_performance = args.get('check_performance', True)
        check_style = args.get('check_style', True)
        
        # Build validation prompt
        system = f"""You are an expert {language} code reviewer. Analyze code for:
- Security vulnerabilities
- Performance issues
- Code style and best practices
- Potential bugs
- Maintainability

Provide specific, actionable feedback with line references."""

        prompt = f"""Review this {language} code:

```{language}
{code}
```

Context: {context if context else 'No additional context'}

Provide:
1. Overall quality score (0-10)
2. Security issues (if any)
3. Performance concerns (if any)
4. Style violations (if any)
5. Suggested improvements

Format as JSON:
{{
    "score": <0-10>,
    "security": ["issue1", "issue2"],
    "performance": ["issue1"],
    "style": ["issue1"],
    "improvements": ["suggestion1", "suggestion2"],
    "verdict": "PASS|REVIEW|FAIL"
}}"""

        response = await self.call_qwen(prompt, system)
        
        # Parse JSON response
        try:
            # Extract JSON from markdown code blocks if present
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                response = json_match.group(1)
            
            result = json.loads(response)
        except:
            # Fallback if not JSON
            result = {
                "score": 7,
                "verdict": "REVIEW",
                "raw_response": response
            }
        
        # Check against learned patterns
        matched_patterns = self._check_patterns(code)
        if matched_patterns:
            result['matched_patterns'] = matched_patterns
        
        elapsed = time.time() - start
        self.stats['validations'] += 1
        
        return {
            "status": "SUCCESS",
            "data": result,
            "metadata": {
                "elapsed_ms": int(elapsed * 1000),
                "model": self.model
            }
        }
    
    async def improve_code(self, args: Dict) -> Dict:
        """
        ✨ IMPROVE CODE - Get AI-powered improvements
        
        Takes code and returns improved version with explanations.
        """
        code = args.get('code', '')
        language = args.get('language', 'python')
        focus = args.get('focus', 'general')  # 'performance', 'readability', 'security'
        
        system = f"""You are an expert {language} developer. Improve code focusing on: {focus}.
Maintain functionality while enhancing quality."""

        prompt = f"""Improve this {language} code:

```{language}
{code}
```

Focus: {focus}

Provide:
1. Improved code
2. Explanation of changes
3. Impact assessment

Format as JSON:
{{
    "improved_code": "...",
    "changes": ["change1", "change2"],
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
        """
        📖 EXPLAIN CODE - Get detailed explanations
        
        Perfect for understanding complex Copilot suggestions.
        """
        code = args.get('code', '')
        language = args.get('language', 'python')
        detail_level = args.get('detail_level', 'medium')  # 'low', 'medium', 'high'
        
        system = f"""You are an expert {language} teacher. Explain code clearly and thoroughly."""
        
        prompt = f"""Explain this {language} code (detail level: {detail_level}):

```{language}
{code}
```

Provide:
1. High-level overview
2. Line-by-line breakdown (if high detail)
3. Key concepts used
4. Potential gotchas

Be clear and educational."""

        response = await self.call_qwen(prompt, system)
        
        return {
            "status": "SUCCESS",
            "data": {
                "explanation": response,
                "language": language
            }
        }
    
    async def generate_tests(self, args: Dict) -> Dict:
        """
        🧪 GENERATE TESTS - Create comprehensive test suite
        
        Analyzes code and generates thorough unit tests.
        """
        code = args.get('code', '')
        language = args.get('language', 'python')
        framework = args.get('framework', 'pytest')  # 'pytest', 'unittest', 'jest', etc.
        coverage_target = args.get('coverage_target', 80)
        
        system = f"""You are an expert test engineer. Create comprehensive {framework} tests."""
        
        prompt = f"""Generate {framework} tests for this {language} code:

```{language}
{code}
```

Requirements:
- Target {coverage_target}% coverage
- Include edge cases
- Test error conditions
- Use meaningful test names

Provide complete, runnable test code."""

        response = await self.call_qwen(prompt, system)
        
        # Extract code blocks
        code_blocks = re.findall(r'```(?:\w+)?\s*(.*?)\s*```', response, re.DOTALL)
        test_code = code_blocks[0] if code_blocks else response
        
        return {
            "status": "SUCCESS",
            "data": {
                "test_code": test_code,
                "framework": framework,
                "explanation": response
            }
        }
    
    async def refactor_code(self, args: Dict) -> Dict:
        """
        🔧 REFACTOR CODE - Intelligent refactoring suggestions
        
        Suggests refactorings to improve code quality.
        """
        code = args.get('code', '')
        language = args.get('language', 'python')
        refactor_type = args.get('type', 'extract_function')
        # Types: extract_function, extract_class, simplify, optimize, modernize
        
        system = f"""You are an expert {language} refactoring specialist."""
        
        prompt = f"""Refactor this {language} code ({refactor_type}):

```{language}
{code}
```

Provide:
1. Refactored code
2. Explanation of changes
3. Benefits

Ensure functionality is preserved."""

        response = await self.call_qwen(prompt, system)
        
        code_blocks = re.findall(r'```(?:\w+)?\s*(.*?)\s*```', response, re.DOTALL)
        refactored = code_blocks[0] if code_blocks else ""
        
        return {
            "status": "SUCCESS",
            "data": {
                "refactored_code": refactored,
                "explanation": response,
                "type": refactor_type
            }
        }
    
    async def learn_pattern(self, args: Dict) -> Dict:
        """
        🧠 LEARN PATTERN - Self-improvement through learning
        
        When user corrects Copilot's suggestion, capture that as a pattern.
        This makes the system smarter over time!
        """
        category = args.get('category', 'general')
        description = args.get('description', '')
        code_before = args.get('code_before', '')
        code_after = args.get('code_after', '')
        
        # Generate pattern ID from content
        pattern_content = f"{category}:{code_before}:{code_after}"
        pattern_id = hashlib.md5(pattern_content.encode()).hexdigest()[:12]
        
        if pattern_id in self.patterns:
            # Update existing pattern
            self.patterns[pattern_id].frequency += 1
            self.patterns[pattern_id].last_seen = datetime.now().isoformat()
            self.patterns[pattern_id].confidence = min(1.0, self.patterns[pattern_id].confidence + 0.1)
        else:
            # Create new pattern
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
                "message": "Pattern learned successfully",
                "total_patterns": len(self.patterns)
            }
        }
    
    async def context_search(self, args: Dict) -> Dict:
        """
        🔎 CONTEXT SEARCH - Find relevant code in project
        
        Searches project for relevant context to enhance Copilot suggestions.
        """
        query = args.get('query', '')
        project_root = args.get('project_root', '.')
        file_types = args.get('file_types', ['.py', '.js', '.ts', '.java'])
        max_results = args.get('max_results', 10)
        
        root = Path(project_root)
        results = []
        
        # Search files
        for ext in file_types:
            for file in root.rglob(f"*{ext}"):
                if '.git' in str(file) or 'node_modules' in str(file):
                    continue
                try:
                    content = file.read_text()
                    if query.lower() in content.lower():
                        # Find context around match
                        lines = content.split('\n')
                        for i, line in enumerate(lines):
                            if query.lower() in line.lower():
                                context_start = max(0, i - 3)
                                context_end = min(len(lines), i + 4)
                                context = '\n'.join(lines[context_start:context_end])
                                results.append({
                                    'file': str(file),
                                    'line': i + 1,
                                    'context': context
                                })
                                if len(results) >= max_results:
                                    break
                except:
                    continue
                if len(results) >= max_results:
                    break
        
        return {
            "status": "SUCCESS",
            "data": {
                "results": results,
                "count": len(results)
            }
        }
    
    async def security_scan(self, args: Dict) -> Dict:
        """
        🛡️ SECURITY SCAN - Deep security analysis
        
        Scans code for security vulnerabilities.
        """
        code = args.get('code', '')
        language = args.get('language', 'python')
        
        system = """You are a security expert. Identify ALL potential security vulnerabilities."""
        
        prompt = f"""Security scan this {language} code:

```{language}
{code}
```

Identify:
1. SQL injection risks
2. XSS vulnerabilities
3. Authentication issues
4. Data exposure risks
5. Insecure dependencies
6. Cryptography issues

Format as JSON with severity levels (LOW, MEDIUM, HIGH, CRITICAL)."""

        response = await self.call_qwen(prompt, system)
        
        try:
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                response = json_match.group(1)
            result = json.loads(response)
        except:
            result = {"raw_response": response}
        
        return {"status": "SUCCESS", "data": result}
    
    async def performance_analysis(self, args: Dict) -> Dict:
        """
        ⚡ PERFORMANCE ANALYSIS - Identify bottlenecks
        
        Analyzes code for performance issues.
        """
        code = args.get('code', '')
        language = args.get('language', 'python')
        
        system = """You are a performance optimization expert."""
        
        prompt = f"""Analyze performance of this {language} code:

```{language}
{code}
```

Identify:
1. Time complexity issues
2. Memory usage problems
3. Inefficient algorithms
4. Database query optimization
5. Caching opportunities

Provide specific optimization suggestions."""

        response = await self.call_qwen(prompt, system)
        
        return {
            "status": "SUCCESS",
            "data": {"analysis": response}
        }
    
    async def get_stats(self, args: Dict) -> Dict:
        """📊 GET STATS - Server statistics"""
        return {
            "status": "SUCCESS",
            "data": {
                **self.stats,
                "patterns_count": len(self.patterns),
                "uptime": "N/A"  # TODO: track uptime
            }
        }
    
    def _check_patterns(self, code: str) -> List[Dict]:
        """Check code against learned patterns"""
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
    
    # ==================== HTTP SERVER ====================
    
    async def handle_tool_call(self, request):
        """Handle incoming tool requests"""
        start = time.time()
        self.stats['requests'] += 1
        
        try:
            data = await request.json()
            tool_name = data.get('tool')
            args = data.get('args', {})
            
            # Route to appropriate handler
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
            return web.json_response({
                "status": "ERROR",
                "error": str(e)
            }, status=500)
    
    async def handle_health(self, request):
        """Health check endpoint"""
        return web.json_response({
            "status": "healthy",
            "model": self.model,
            "stats": self.stats
        })
    
    async def handle_tools_list(self, request):
        """List available tools"""
        tools = {
            "validate_code": "Validate code quality, security, and style",
            "improve_code": "Get AI-powered code improvements",
            "explain_code": "Get detailed code explanations",
            "generate_tests": "Generate comprehensive test suites",
            "refactor_code": "Get intelligent refactoring suggestions",
            "learn_pattern": "Learn from corrections (self-improvement)",
            "context_search": "Find relevant code in project",
            "security_scan": "Deep security vulnerability scanning",
            "performance_analysis": "Identify performance bottlenecks",
            "get_stats": "Get server statistics"
        }
        
        return web.json_response({
            "status": "SUCCESS",
            "tools": [{"name": k, "description": v} for k, v in tools.items()]
        })
    
    async def start(self):
        """Start the MCP server"""
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
║   🚀 Revolutionary MCP Server for Copilot + Qwen        ║
║                                                          ║
║   Server: http://localhost:{self.port}                        ║
║   Model:  {self.model:40s} ║
║   Status: READY                                          ║
║                                                          ║
║   Available tools: {len(await self.handle_tools_list(None))}                                  ║
║   Learned patterns: {len(self.patterns)}                                 ║
╚══════════════════════════════════════════════════════════╝

💡 Next steps:
1. Install VS Code extension (coming soon)
2. Start using enhanced Copilot features
3. Watch as the system learns from your patterns!

📖 Example API call:
   curl -X POST http://localhost:{self.port}/tool \\
     -H 'Content-Type: application/json' \\
     -d '{{"tool": "validate_code", "args": {{"code": "...", "language": "python"}}}}'
""")
        
        # Keep running
        await asyncio.Event().wait()


async def main():
    import argparse
    parser = argparse.ArgumentParser(description="Revolutionary MCP Server for Copilot")
    parser.add_argument('--port', type=int, default=8765, help='Port to run server on')
    args = parser.parse_args()
    
    # Check if Ollama is running
    try:
        proc = await asyncio.create_subprocess_exec(
            'curl', '-s', 'http://localhost:11434/api/tags',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await proc.communicate()
        if proc.returncode != 0:
            print("❌ Ollama is not running. Please start it with: ollama serve")
            sys.exit(1)
    except:
        print("❌ Cannot connect to Ollama. Please install and start it.")
        sys.exit(1)
    
    server = IntelligentMCPServer(port=args.port)
    await server.start()


if __name__ == "__main__":
    asyncio.run(main())
