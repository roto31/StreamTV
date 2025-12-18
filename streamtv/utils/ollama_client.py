"""Ollama AI client for log analysis and error troubleshooting"""

import httpx
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class OllamaClient:
    """Client for interacting with Ollama AI for log analysis and troubleshooting"""
    
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3.2:latest"):
        """
        Initialize Ollama client
        
        Args:
            base_url: Ollama API base URL (default: http://localhost:11434)
            model: Model to use for analysis (default: llama3.2:latest)
        """
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.client = httpx.AsyncClient(timeout=60.0)
        logger.info(f"Initialized Ollama client with base_url={base_url}, model={model}")
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    async def is_available(self) -> bool:
        """Check if Ollama is available and responsive"""
        try:
            response = await self.client.get(f"{self.base_url}/api/tags")
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Ollama not available: {e}")
            return False
    
    async def list_models(self) -> List[str]:
        """List available models"""
        try:
            response = await self.client.get(f"{self.base_url}/api/tags")
            if response.status_code == 200:
                data = response.json()
                return [model['name'] for model in data.get('models', [])]
            return []
        except Exception as e:
            logger.error(f"Error listing models: {e}")
            return []
    
    async def analyze_error(
        self,
        error_message: str,
        context: Optional[Dict[str, Any]] = None,
        log_excerpt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze an error using Ollama AI
        
        Args:
            error_message: The error message to analyze
            context: Additional context (file, function, component, etc.)
            log_excerpt: Relevant log excerpt surrounding the error
        
        Returns:
            Dict with analysis results including:
            - root_cause: Identified root cause
            - severity: Error severity (critical, high, medium, low)
            - fix_suggestions: List of fix suggestions
            - confidence: AI confidence level (0-1)
        """
        try:
            # Build analysis prompt
            prompt = self._build_error_analysis_prompt(error_message, context, log_excerpt)
            
            # Query Ollama
            response = await self._generate(prompt)
            
            # Parse response
            analysis = self._parse_error_analysis(response)
            
            logger.info(f"Error analysis completed: {analysis.get('root_cause', 'Unknown')[:100]}")
            return analysis
            
        except Exception as e:
            logger.error(f"Error during Ollama analysis: {e}")
            return {
                'root_cause': 'Unknown - AI analysis failed',
                'severity': 'medium',
                'fix_suggestions': [],
                'confidence': 0.0,
                'error': str(e)
            }
    
    async def suggest_fix(
        self,
        error_type: str,
        error_details: str,
        current_config: Optional[Dict[str, Any]] = None,
        code_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get AI-powered fix suggestions for a specific error
        
        Args:
            error_type: Type of error (timeout, connection, ffmpeg, etc.)
            error_details: Detailed error information
            current_config: Current configuration values
            code_context: Relevant code snippet
        
        Returns:
            Dict with fix suggestions including:
            - fix_type: Type of fix (config, code, dependency, etc.)
            - changes: Specific changes to make
            - rationale: Why this fix should work
            - risks: Potential risks of applying the fix
        """
        try:
            prompt = self._build_fix_suggestion_prompt(
                error_type, error_details, current_config, code_context
            )
            
            response = await self._generate(prompt)
            fix = self._parse_fix_suggestion(response)
            
            logger.info(f"Fix suggestion generated: {fix.get('fix_type', 'unknown')}")
            return fix
            
        except Exception as e:
            logger.error(f"Error generating fix suggestion: {e}")
            return {
                'fix_type': 'unknown',
                'changes': [],
                'rationale': 'AI fix generation failed',
                'risks': ['Unknown - manual intervention recommended'],
                'error': str(e)
            }
    
    async def analyze_log_pattern(
        self,
        log_lines: List[str],
        timeframe: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze log patterns to identify recurring issues
        
        Args:
            log_lines: List of log lines to analyze
            timeframe: Timeframe description (e.g., "last 1 hour")
        
        Returns:
            Dict with pattern analysis including:
            - patterns: List of identified patterns
            - trends: Identified trends
            - recommendations: Proactive recommendations
        """
        try:
            prompt = self._build_pattern_analysis_prompt(log_lines, timeframe)
            response = await self._generate(prompt)
            analysis = self._parse_pattern_analysis(response)
            
            logger.info(f"Pattern analysis completed: {len(analysis.get('patterns', []))} patterns found")
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing log patterns: {e}")
            return {
                'patterns': [],
                'trends': [],
                'recommendations': [],
                'error': str(e)
            }
    
    async def _generate(self, prompt: str) -> str:
        """Generate response from Ollama"""
        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.3,  # Lower temperature for more deterministic analysis
                    "top_p": 0.9,
                    "num_predict": 1000  # Max tokens for response
                }
            }
            
            response = await self.client.post(
                f"{self.base_url}/api/generate",
                json=payload
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get('response', '')
            else:
                logger.error(f"Ollama API error: {response.status_code} - {response.text}")
                return ''
                
        except Exception as e:
            logger.error(f"Error calling Ollama API: {e}")
            raise
    
    def _build_error_analysis_prompt(
        self,
        error_message: str,
        context: Optional[Dict[str, Any]],
        log_excerpt: Optional[str]
    ) -> str:
        """Build prompt for error analysis"""
        prompt = f"""You are an expert system administrator analyzing errors in a video streaming server (StreamTV).

ERROR MESSAGE:
{error_message}
"""
        
        if context:
            prompt += f"\nCONTEXT:\n"
            for key, value in context.items():
                prompt += f"- {key}: {value}\n"
        
        if log_excerpt:
            prompt += f"\nRELATED LOG EXCERPT:\n{log_excerpt}\n"
        
        prompt += """
Please analyze this error and provide:

1. ROOT CAUSE: What is the underlying cause of this error?
2. SEVERITY: Rate the severity (critical/high/medium/low)
3. FIX SUGGESTIONS: List 3-5 specific ways to fix this issue
4. CONFIDENCE: Your confidence level (0.0-1.0)

Format your response as JSON:
{
  "root_cause": "...",
  "severity": "...",
  "fix_suggestions": ["...", "..."],
  "confidence": 0.0
}
"""
        return prompt
    
    def _build_fix_suggestion_prompt(
        self,
        error_type: str,
        error_details: str,
        current_config: Optional[Dict[str, Any]],
        code_context: Optional[str]
    ) -> str:
        """Build prompt for fix suggestions"""
        prompt = f"""You are an expert system administrator fixing errors in a video streaming server (StreamTV).

ERROR TYPE: {error_type}

ERROR DETAILS:
{error_details}
"""
        
        if current_config:
            prompt += f"\nCURRENT CONFIGURATION:\n{json.dumps(current_config, indent=2)}\n"
        
        if code_context:
            prompt += f"\nRELEVANT CODE:\n{code_context}\n"
        
        prompt += """
Please suggest a fix for this error. Provide:

1. FIX TYPE: config/code/dependency/restart/other
2. CHANGES: Specific changes to make (be precise)
3. RATIONALE: Why this fix should work
4. RISKS: Potential risks or side effects

Format your response as JSON:
{
  "fix_type": "...",
  "changes": [
    {"target": "...", "change": "...", "value": "..."}
  ],
  "rationale": "...",
  "risks": ["..."]
}
"""
        return prompt
    
    def _build_pattern_analysis_prompt(
        self,
        log_lines: List[str],
        timeframe: Optional[str]
    ) -> str:
        """Build prompt for pattern analysis"""
        log_sample = '\n'.join(log_lines[:500])  # Limit to 500 lines
        
        prompt = f"""You are an expert system administrator analyzing log patterns in a video streaming server (StreamTV).

TIMEFRAME: {timeframe or 'Recent logs'}

LOG SAMPLE ({len(log_lines)} lines):
{log_sample}

Please analyze these logs and identify:

1. PATTERNS: Recurring error patterns or issues
2. TRENDS: Are errors increasing, decreasing, or stable?
3. RECOMMENDATIONS: Proactive steps to prevent issues

Format your response as JSON:
{{
  "patterns": [
    {{"pattern": "...", "frequency": "...", "severity": "..."}}
  ],
  "trends": [
    {{"trend": "...", "description": "..."}}
  ],
  "recommendations": ["...", "..."]
}}
"""
        return prompt
    
    def _parse_error_analysis(self, response: str) -> Dict[str, Any]:
        """Parse error analysis response"""
        try:
            # Try to extract JSON from response
            response = response.strip()
            
            # Find JSON block
            start = response.find('{')
            end = response.rfind('}') + 1
            if start != -1 and end > start:
                json_str = response[start:end]
                return json.loads(json_str)
            
            # Fallback: parse manually
            return {
                'root_cause': response[:200],
                'severity': 'medium',
                'fix_suggestions': [response[200:400]] if len(response) > 200 else [],
                'confidence': 0.5
            }
            
        except Exception as e:
            logger.error(f"Error parsing analysis response: {e}")
            return {
                'root_cause': response[:200] if response else 'Unknown',
                'severity': 'medium',
                'fix_suggestions': [],
                'confidence': 0.3
            }
    
    def _parse_fix_suggestion(self, response: str) -> Dict[str, Any]:
        """Parse fix suggestion response"""
        try:
            response = response.strip()
            start = response.find('{')
            end = response.rfind('}') + 1
            if start != -1 and end > start:
                json_str = response[start:end]
                return json.loads(json_str)
            
            return {
                'fix_type': 'manual',
                'changes': [{'target': 'unknown', 'change': response[:200], 'value': ''}],
                'rationale': response[200:400] if len(response) > 200 else 'See AI response',
                'risks': ['Manual review required']
            }
            
        except Exception as e:
            logger.error(f"Error parsing fix suggestion: {e}")
            return {
                'fix_type': 'manual',
                'changes': [],
                'rationale': response[:200] if response else 'Unknown',
                'risks': ['Parsing failed - manual intervention required']
            }
    
    def _parse_pattern_analysis(self, response: str) -> Dict[str, Any]:
        """Parse pattern analysis response"""
        try:
            response = response.strip()
            start = response.find('{')
            end = response.rfind('}') + 1
            if start != -1 and end > start:
                json_str = response[start:end]
                return json.loads(json_str)
            
            return {
                'patterns': [],
                'trends': [],
                'recommendations': [response[:200]] if response else []
            }
            
        except Exception as e:
            logger.error(f"Error parsing pattern analysis: {e}")
            return {
                'patterns': [],
                'trends': [],
                'recommendations': []
            }

