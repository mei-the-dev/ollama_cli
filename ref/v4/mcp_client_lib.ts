/**
 * MCP Client Library for GitHub Copilot
 * =====================================
 * 
 * This library provides easy integration between GitHub Copilot Chat
 * and the revolutionary MCP server running Qwen2.5-coder.
 * 
 * Usage in Copilot Chat:
 * ----------------------
 * @workspace /validate - Validate selected code
 * @workspace /improve - Get improvement suggestions
 * @workspace /explain - Explain complex code
 * @workspace /test - Generate tests
 */

interface MCPResponse {
  status: 'SUCCESS' | 'ERROR';
  data?: any;
  error?: string;
  metadata?: any;
}

interface ValidationResult {
  score: number;
  security: string[];
  performance: string[];
  style: string[];
  improvements: string[];
  verdict: 'PASS' | 'REVIEW' | 'FAIL';
  matched_patterns?: Array<{
    pattern_id: string;
    category: string;
    suggestion: string;
    confidence: number;
  }>;
}

class MCPClient {
  private baseUrl: string;
  
  constructor(baseUrl: string = 'http://localhost:8765') {
    this.baseUrl = baseUrl;
  }
  
  /**
   * Validate code using Qwen AI
   */
  async validateCode(
    code: string,
    language: string = 'python',
    options: {
      checkSecurity?: boolean;
      checkPerformance?: boolean;
      checkStyle?: boolean;
      context?: string;
    } = {}
  ): Promise<ValidationResult> {
    const response = await this.callTool('validate_code', {
      code,
      language,
      check_security: options.checkSecurity ?? true,
      check_performance: options.checkPerformance ?? true,
      check_style: options.checkStyle ?? true,
      context: options.context ?? ''
    });
    
    return response.data as ValidationResult;
  }
  
  /**
   * Get AI-powered improvements for code
   */
  async improveCode(
    code: string,
    language: string = 'python',
    focus: 'performance' | 'readability' | 'security' | 'general' = 'general'
  ): Promise<{
    improved_code: string;
    changes: string[];
    impact: string;
  }> {
    const response = await this.callTool('improve_code', {
      code,
      language,
      focus
    });
    
    return response.data;
  }
  
  /**
   * Explain code in natural language
   */
  async explainCode(
    code: string,
    language: string = 'python',
    detailLevel: 'low' | 'medium' | 'high' = 'medium'
  ): Promise<{
    explanation: string;
    language: string;
  }> {
    const response = await this.callTool('explain_code', {
      code,
      language,
      detail_level: detailLevel
    });
    
    return response.data;
  }
  
  /**
   * Generate comprehensive tests
   */
  async generateTests(
    code: string,
    language: string = 'python',
    framework: string = 'pytest',
    coverageTarget: number = 80
  ): Promise<{
    test_code: string;
    framework: string;
    explanation: string;
  }> {
    const response = await this.callTool('generate_tests', {
      code,
      language,
      framework,
      coverage_target: coverageTarget
    });
    
    return response.data;
  }
  
  /**
   * Get refactoring suggestions
   */
  async refactorCode(
    code: string,
    language: string = 'python',
    refactorType: 'extract_function' | 'extract_class' | 'simplify' | 'optimize' | 'modernize' = 'extract_function'
  ): Promise<{
    refactored_code: string;
    explanation: string;
    type: string;
  }> {
    const response = await this.callTool('refactor_code', {
      code,
      language,
      type: refactorType
    });
    
    return response.data;
  }
  
  /**
   * Learn from user correction (self-improvement!)
   */
  async learnPattern(
    codeBefore: string,
    codeAfter: string,
    category: 'naming' | 'style' | 'architecture' | 'anti-pattern' = 'general',
    description: string = ''
  ): Promise<{
    pattern_id: string;
    message: string;
    total_patterns: number;
  }> {
    const response = await this.callTool('learn_pattern', {
      code_before: codeBefore,
      code_after: codeAfter,
      category,
      description
    });
    
    return response.data;
  }
  
  /**
   * Search project for relevant context
   */
  async searchContext(
    query: string,
    projectRoot: string = '.',
    fileTypes: string[] = ['.py', '.js', '.ts'],
    maxResults: number = 10
  ): Promise<{
    results: Array<{
      file: string;
      line: number;
      context: string;
    }>;
    count: number;
  }> {
    const response = await this.callTool('context_search', {
      query,
      project_root: projectRoot,
      file_types: fileTypes,
      max_results: maxResults
    });
    
    return response.data;
  }
  
  /**
   * Deep security scanning
   */
  async securityScan(
    code: string,
    language: string = 'python'
  ): Promise<any> {
    const response = await this.callTool('security_scan', {
      code,
      language
    });
    
    return response.data;
  }
  
  /**
   * Performance analysis
   */
  async analyzePerformance(
    code: string,
    language: string = 'python'
  ): Promise<{
    analysis: string;
  }> {
    const response = await this.callTool('performance_analysis', {
      code,
      language
    });
    
    return response.data;
  }
  
  /**
   * Get server statistics
   */
  async getStats(): Promise<{
    requests: number;
    validations: number;
    improvements_suggested: number;
    patterns_learned: number;
    patterns_count: number;
    avg_response_time: number;
  }> {
    const response = await this.callTool('get_stats', {});
    return response.data;
  }
  
  /**
   * List available tools
   */
  async listTools(): Promise<Array<{name: string; description: string}>> {
    const response = await fetch(`${this.baseUrl}/tools`);
    const data = await response.json();
    return data.tools;
  }
  
  /**
   * Health check
   */
  async health(): Promise<{status: string; model: string; stats: any}> {
    const response = await fetch(`${this.baseUrl}/health`);
    return await response.json();
  }
  
  /**
   * Low-level tool call
   */
  private async callTool(tool: string, args: any): Promise<MCPResponse> {
    const response = await fetch(`${this.baseUrl}/tool`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ tool, args })
    });
    
    if (!response.ok) {
      throw new Error(`MCP call failed: ${response.status}`);
    }
    
    return await response.json();
  }
}

// ============= COPILOT CHAT INTEGRATION =============

/**
 * Example Copilot Chat participant that uses MCP
 */
export function registerCopilotParticipant(context: any) {
  const mcp = new MCPClient();
  
  // Register chat participant
  const participant = context.registerChatParticipant('copilot-mcp', async (
    request: any,
    context: any,
    response: any,
    token: any
  ) => {
    const command = request.command;
    const selectedCode = context.selection?.text || '';
    const language = context.language || 'python';
    
    try {
      switch (command) {
        case 'validate':
          response.markdown('🔍 Validating code with Qwen AI...\n\n');
          const validation = await mcp.validateCode(selectedCode, language);
          
          response.markdown(`### Validation Results\n\n`);
          response.markdown(`**Score:** ${validation.score}/10\n`);
          response.markdown(`**Verdict:** ${validation.verdict}\n\n`);
          
          if (validation.security.length > 0) {
            response.markdown(`#### 🛡️ Security Issues:\n`);
            validation.security.forEach(issue => {
              response.markdown(`- ${issue}\n`);
            });
          }
          
          if (validation.improvements.length > 0) {
            response.markdown(`\n#### ✨ Suggested Improvements:\n`);
            validation.improvements.forEach(imp => {
              response.markdown(`- ${imp}\n`);
            });
          }
          
          if (validation.matched_patterns && validation.matched_patterns.length > 0) {
            response.markdown(`\n#### 🧠 Learned Patterns Matched:\n`);
            validation.matched_patterns.forEach(p => {
              response.markdown(`- ${p.category}: ${p.suggestion} (confidence: ${p.confidence})\n`);
            });
          }
          break;
          
        case 'improve':
          response.markdown('✨ Getting AI improvements...\n\n');
          const improved = await mcp.improveCode(selectedCode, language);
          
          response.markdown(`### Improved Code\n\n`);
          response.markdown('```' + language + '\n' + improved.improved_code + '\n```\n\n');
          response.markdown(`#### Changes:\n`);
          improved.changes.forEach(change => {
            response.markdown(`- ${change}\n`);
          });
          response.markdown(`\n**Impact:** ${improved.impact}\n`);
          break;
          
        case 'explain':
          response.markdown('📖 Explaining code...\n\n');
          const explanation = await mcp.explainCode(selectedCode, language);
          response.markdown(explanation.explanation);
          break;
          
        case 'test':
          response.markdown('🧪 Generating tests...\n\n');
          const tests = await mcp.generateTests(selectedCode, language);
          response.markdown('```' + language + '\n' + tests.test_code + '\n```\n\n');
          response.markdown(tests.explanation);
          break;
          
        case 'security':
          response.markdown('🛡️ Running security scan...\n\n');
          const securityResults = await mcp.securityScan(selectedCode, language);
          response.markdown(JSON.stringify(securityResults, null, 2));
          break;
          
        case 'stats':
          response.markdown('📊 MCP Server Statistics\n\n');
          const stats = await mcp.getStats();
          response.markdown(`- Total requests: ${stats.requests}\n`);
          response.markdown(`- Validations: ${stats.validations}\n`);
          response.markdown(`- Improvements suggested: ${stats.improvements_suggested}\n`);
          response.markdown(`- Patterns learned: ${stats.patterns_learned}\n`);
          response.markdown(`- Average response time: ${stats.avg_response_time.toFixed(2)}s\n`);
          break;
          
        default:
          response.markdown('Available commands:\n');
          response.markdown('- `/validate` - Validate code\n');
          response.markdown('- `/improve` - Get improvements\n');
          response.markdown('- `/explain` - Explain code\n');
          response.markdown('- `/test` - Generate tests\n');
          response.markdown('- `/security` - Security scan\n');
          response.markdown('- `/stats` - Show statistics\n');
      }
    } catch (error) {
      response.markdown(`❌ Error: ${error.message}`);
    }
  });
  
  return participant;
}

export default MCPClient;
