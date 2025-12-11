#!/usr/bin/env python3
"""
Auto-Healing CLI - Monitors logs, detects errors, and applies fixes automatically

Usage:
    # Run health check (dry-run, no fixes applied)
    python scripts/auto_heal.py

    # Run health check and apply fixes
    python scripts/auto_heal.py --apply

    # Run continuous monitoring
    python scripts/auto_heal.py --continuous --interval 30

    # Use custom Ollama URL/model
    python scripts/auto_heal.py --ollama-url http://localhost:11434 --ollama-model llama3.2:latest

    # Disable AI analysis
    python scripts/auto_heal.py --no-ai
"""

import asyncio
import argparse
import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from streamtv.utils.auto_healer import AutoHealer


def print_banner():
    """Print banner"""
    print("╔════════════════════════════════════════════════════════════════╗")
    print("║                                                                ║")
    print("║           StreamTV Auto-Healing System v1.0                    ║")
    print("║        Powered by Ollama AI Log Analysis                      ║")
    print("║                                                                ║")
    print("╚════════════════════════════════════════════════════════════════╝")
    print()


def print_results(result: dict):
    """Print health check results in a readable format"""
    print("\n" + "=" * 70)
    print("HEALTH CHECK RESULTS")
    print("=" * 70)
    
    # Summary
    summary = result.get('summary', {})
    status = summary.get('status', 'unknown')
    
    status_emoji = {
        'healthy': '✅',
        'healing': '🔧',
        'degraded': '⚠️',
        'critical': '🚨',
        'error': '❌'
    }
    
    print(f"\nStatus: {status_emoji.get(status, '❓')} {status.upper()}")
    print(f"Errors Detected: {summary.get('errors_detected', 0)}")
    print(f"High Priority: {summary.get('high_priority', 0)}")
    print(f"Fixes Applied: {summary.get('fixes_applied', 0)}")
    
    if summary.get('ai_analyses_performed', 0) > 0:
        print(f"AI Analyses: {summary['ai_analyses_performed']}")
    
    # Ollama status
    if result.get('ai_enabled'):
        ollama_status = "✅ Available" if result.get('ollama_available') else "❌ Unavailable"
        print(f"Ollama: {ollama_status}")
    
    # Error breakdown
    grouped = result.get('grouped_errors', {})
    if grouped:
        print(f"\nError Breakdown by Category:")
        for category, errors in grouped.items():
            print(f"  - {category}: {len(errors)} error(s)")
    
    # Fixes applied
    fixes_applied = result.get('fixes_applied', [])
    if fixes_applied:
        print(f"\nFixes Applied:")
        for fix in fixes_applied:
            if fix.get('success'):
                fixes_count = len(fix.get('fixes_applied', []))
                pattern = fix.get('error_pattern', 'unknown')
                print(f"  ✅ {pattern}: {fixes_count} fix(es)")
            else:
                pattern = fix.get('error_pattern', 'unknown')
                print(f"  ❌ {pattern}: no fix available")
    
    # Recommendations
    recommendations = summary.get('recommendations', [])
    if recommendations:
        print(f"\nRecommendations:")
        for rec in recommendations:
            print(f"  {rec}")
    
    # Dry run warning
    if result.get('dry_run'):
        print("\n⚠️  DRY RUN MODE: No changes were actually applied")
        print("   Run with --apply to apply fixes")
    
    print("\n" + "=" * 70)


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='StreamTV Auto-Healing System - AI-powered error detection and fixing',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        '--apply',
        action='store_true',
        help='Apply fixes (default: dry-run only)'
    )
    
    parser.add_argument(
        '--continuous',
        action='store_true',
        help='Run continuous monitoring'
    )
    
    parser.add_argument(
        '--interval',
        type=int,
        default=30,
        help='Interval between checks in minutes (default: 30)'
    )
    
    parser.add_argument(
        '--max-iterations',
        type=int,
        default=None,
        help='Max iterations for continuous mode (default: infinite)'
    )
    
    parser.add_argument(
        '--ollama-url',
        type=str,
        default='http://localhost:11434',
        help='Ollama API URL (default: http://localhost:11434)'
    )
    
    parser.add_argument(
        '--ollama-model',
        type=str,
        default='llama3.2:latest',
        help='Ollama model to use (default: llama3.2:latest)'
    )
    
    parser.add_argument(
        '--no-ai',
        action='store_true',
        help='Disable AI analysis (use only registered fixes)'
    )
    
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output results as JSON'
    )
    
    parser.add_argument(
        '--workspace',
        type=str,
        default=None,
        help='Workspace root directory (default: auto-detect)'
    )
    
    args = parser.parse_args()
    
    # Determine workspace root
    if args.workspace:
        workspace_root = Path(args.workspace)
    else:
        # Auto-detect: go up from scripts/ to project root
        workspace_root = Path(__file__).parent.parent
    
    if not workspace_root.exists():
        print(f"❌ Error: Workspace not found: {workspace_root}")
        return 1
    
    # Print banner (unless JSON output)
    if not args.json:
        print_banner()
        
        mode = "APPLY MODE" if args.apply else "DRY-RUN MODE"
        ai_status = "DISABLED" if args.no_ai else "ENABLED"
        
        print(f"Mode: {mode}")
        print(f"AI Analysis: {ai_status}")
        print(f"Workspace: {workspace_root}")
        print(f"Ollama: {args.ollama_url} ({args.ollama_model})")
        print()
    
    # Initialize auto-healer
    async with AutoHealer(
        workspace_root=workspace_root,
        ollama_url=args.ollama_url,
        ollama_model=args.ollama_model,
        dry_run=not args.apply,
        enable_ai=not args.no_ai
    ) as healer:
        
        if args.continuous:
            # Run continuous monitoring
            if not args.json:
                print(f"Starting continuous monitoring (interval={args.interval}min)...")
                print("Press Ctrl+C to stop\n")
            
            await healer.run_continuous_monitoring(
                interval_minutes=args.interval,
                max_iterations=args.max_iterations
            )
        
        else:
            # Run single health check
            result = await healer.run_health_check()
            
            # Output results
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                print_results(result)
            
            # Get stats
            if not args.json:
                stats = healer.get_stats()
                print(f"\nAuto-Healer Stats:")
                print(f"  Total runs: {stats['run_count']}")
                print(f"  Total errors detected: {stats['total_errors_detected']}")
                print(f"  Total fixes applied: {stats['total_fixes_applied']}")
    
    return 0


if __name__ == '__main__':
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

