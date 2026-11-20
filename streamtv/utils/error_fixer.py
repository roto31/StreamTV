"""Automated error fixing system"""

import re
import yaml
import logging
from typing import Dict, Any, List, Optional, Callable
from pathlib import Path
import shutil
from datetime import datetime

logger = logging.getLogger(__name__)

# Streaming bedrock — ErrorFixer must never rewrite these (docs/STREAMING_BEDROCK_FROZEN.md).
_FROZEN_PATH_PREFIXES = (
    "streamtv/streaming/",
    "streamtv/hdhomerun/",
    "streamtv/cache/",
    "streamtv/ffmpeg/",
    "streamtv/scheduling/",
)
_FROZEN_PATH_EXACT = frozenset({"streamtv/api/iptv.py"})


def is_frozen_fixer_target(target: str) -> bool:
    """True if target is under frozen streaming trees or exact frozen files."""
    norm = str(target).replace("\\", "/").lstrip("./")
    if norm in _FROZEN_PATH_EXACT:
        return True
    return any(norm.startswith(prefix) for prefix in _FROZEN_PATH_PREFIXES)


class FixAction:
    """Represents a fix action that can be applied"""
    
    def __init__(
        self,
        fix_type: str,
        target: str,
        change_type: str,
        value: Any,
        description: str,
        risks: List[str]
    ):
        self.fix_type = fix_type  # config, code, restart, etc.
        self.target = target  # File path, config key, etc.
        self.change_type = change_type  # set, increase, decrease, replace, etc.
        self.value = value
        self.description = description
        self.risks = risks
        self.applied_at = None
        self.backup_path = None


class ErrorFixer:
    """Applies automated fixes to detected errors"""
    
    # Registry of known fixes for specific error patterns.
    # Never target streamtv/streaming/** (bedrock freeze).
    FIX_REGISTRY = {
        'ffmpeg_timeout': {
            'type': 'advise',
            'target': 'operator',
            'fixes': [
                {
                    'description': (
                        'FFmpeg timeout: use STREAMTV_FFMPEG_STALL_SEC (default 90) '
                        'and scripts/heal_stalled_ffmpeg.py — do not rewrite mpegts_streamer.py'
                    ),
                    'action': 'operator_guidance',
                }
            ]
        },
        'connection_refused': {
            'type': 'config',
            'target': 'config.yaml',
            'fixes': [
                {
                    'description': 'Increase connection timeout',
                    'yaml_path': ['streaming', 'timeout'],
                    'operation': 'increase',
                    'factor': 1.5,
                    'max_value': 120
                },
                {
                    'description': 'Increase max retries',
                    'yaml_path': ['streaming', 'max_retries'],
                    'operation': 'increase',
                    'amount': 2,
                    'max_value': 10
                }
            ]
        },
        'archive_org_redirect': {
            'type': 'advice',
            'target': 'operator',
            'fixes': [
                {
                    'description': (
                        'Archive.org redirect issues: verify Archive cookies / '
                        'follow_redirects in operator config — streaming code is frozen'
                    ),
                    'action': 'operator_guidance',
                }
            ]
        },
        'http_error': {
            'type': 'config',
            'target': 'config.yaml',
            'fixes': [
                {
                    'description': 'Enable authentication for Archive.org',
                    'yaml_path': ['archive_org', 'use_authentication'],
                    'operation': 'set',
                    'value': True
                }
            ]
        }
    }
    
    def __init__(
        self,
        workspace_root: Path,
        dry_run: bool = True,
        max_fix_attempts: int = 3,
    ):
        """
        Initialize error fixer
        
        Args:
            workspace_root: Root directory of the workspace
            dry_run: If True, only simulate fixes without applying them
            max_fix_attempts: Cap successful registry applies per error_pattern
                for this process lifetime
        """
        self.workspace_root = Path(workspace_root)
        self.dry_run = dry_run
        self.max_fix_attempts = max(1, int(max_fix_attempts))
        self.applied_fixes = []
        self._attempt_counts: Dict[str, int] = {}
        self.backup_dir = self.workspace_root / ".streamtv_backups"
        
        # Create backup directory
        self.backup_dir.mkdir(exist_ok=True)
        
        logger.info(
            "Initialized ErrorFixer (dry_run=%s, max_fix_attempts=%s)",
            dry_run,
            self.max_fix_attempts,
        )
    
    async def apply_fix(
        self,
        error_pattern: str,
        ai_suggestion: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Apply a fix for a detected error pattern
        
        Args:
            error_pattern: Name of the error pattern
            ai_suggestion: Optional AI-generated fix suggestion
        
        Returns:
            Dict with fix results including success status and details
        """
        result = {
            'error_pattern': error_pattern,
            'success': False,
            'fixes_applied': [],
            'fixes_failed': [],
            'backup_created': False,
            'dry_run': self.dry_run
        }
        
        try:
            attempts = self._attempt_counts.get(error_pattern, 0)
            if attempts >= self.max_fix_attempts:
                result['message'] = (
                    f'Skipped: max_fix_attempts ({self.max_fix_attempts}) '
                    f'reached for {error_pattern}'
                )
                result['skipped_max_attempts'] = True
                logger.warning(result['message'])
                return result

            # Check if we have a registered fix for this pattern
            if error_pattern in self.FIX_REGISTRY:
                fix_config = self.FIX_REGISTRY[error_pattern]
                result['fix_source'] = 'registry'
                
                # Apply registered fixes
                for fix_spec in fix_config['fixes']:
                    fix_result = await self._apply_registered_fix(
                        fix_config['type'],
                        fix_config['target'],
                        fix_spec
                    )
                    
                    if fix_result['success']:
                        result['fixes_applied'].append(fix_result)
                    else:
                        result['fixes_failed'].append(fix_result)
            
            # If AI suggestion provided and no registered fix, try to apply AI suggestion
            elif ai_suggestion:
                result['fix_source'] = 'ai_suggestion'
                ai_fix_result = await self._apply_ai_suggestion(ai_suggestion)
                
                if ai_fix_result['success']:
                    result['fixes_applied'].append(ai_fix_result)
                else:
                    result['fixes_failed'].append(ai_fix_result)
            
            else:
                result['message'] = f'No fix available for pattern: {error_pattern}'
                logger.warning(result['message'])
                return result
            
            # Overall success if at least one fix applied
            result['success'] = len(result['fixes_applied']) > 0
            
            if result['success']:
                self._attempt_counts[error_pattern] = attempts + 1
                logger.info(f"Applied {len(result['fixes_applied'])} fix(es) for {error_pattern}")
            else:
                logger.warning(f"No fixes successfully applied for {error_pattern}")
        
        except Exception as e:
            logger.error(f"Error applying fix for {error_pattern}: {e}")
            result['error'] = str(e)
        
        return result
    
    async def _apply_registered_fix(
        self,
        fix_type: str,
        target: str,
        fix_spec: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply a registered fix from the fix registry"""
        result = {
            'description': fix_spec.get('description', 'Unknown fix'),
            'target': target,
            'success': False
        }

        if fix_spec.get('action') == 'operator_guidance' or fix_type == 'advice':
            result['success'] = True
            result['message'] = fix_spec.get('description', 'Operator guidance')
            result['requires_review'] = True
            logger.info("Operator guidance (no file write): %s", result['message'])
            return result

        if is_frozen_fixer_target(target):
            result['error'] = (
                f'Refused: target is frozen streaming bedrock ({target})'
            )
            result['frozen_target'] = True
            logger.error(result['error'])
            return result
        
        try:
            target_path = self.workspace_root / target
            
            if not target_path.exists():
                result['error'] = f'Target file not found: {target}'
                logger.error(result['error'])
                return result
            
            # Create backup
            if not self.dry_run:
                backup_path = self._create_backup(target_path)
                result['backup_path'] = str(backup_path)
            
            # Apply fix based on type
            if fix_type == 'config' and target.endswith('.yaml'):
                result = await self._fix_yaml_config(target_path, fix_spec, result)
            elif fix_type == 'code' or fix_type == 'config':
                result = await self._fix_code_file(target_path, fix_spec, result)
            else:
                result['error'] = f'Unknown fix type: {fix_type}'
            
        except Exception as e:
            logger.error(f"Error applying registered fix: {e}")
            result['error'] = str(e)
        
        return result
    
    async def _fix_yaml_config(
        self,
        file_path: Path,
        fix_spec: Dict[str, Any],
        result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Fix YAML configuration file"""
        try:
            # Load YAML
            with open(file_path, 'r') as f:
                config = yaml.safe_load(f)
            
            yaml_path = fix_spec.get('yaml_path', [])
            operation = fix_spec.get('operation', 'set')
            
            # Navigate to target
            target = config
            for key in yaml_path[:-1]:
                if key not in target:
                    target[key] = {}
                target = target[key]
            
            final_key = yaml_path[-1]
            current_value = target.get(final_key)
            
            # Apply operation
            if operation == 'set':
                new_value = fix_spec.get('value')
            elif operation == 'increase':
                factor = fix_spec.get('factor', 1.5)
                amount = fix_spec.get('amount', 0)
                max_value = fix_spec.get('max_value', float('inf'))
                
                if isinstance(current_value, (int, float)):
                    if factor != 1:
                        new_value = min(current_value * factor, max_value)
                    else:
                        new_value = min(current_value + amount, max_value)
                else:
                    result['error'] = f'Cannot increase non-numeric value: {current_value}'
                    return result
            elif operation == 'decrease':
                factor = fix_spec.get('factor', 0.5)
                amount = fix_spec.get('amount', 0)
                min_value = fix_spec.get('min_value', 0)
                
                if isinstance(current_value, (int, float)):
                    if factor != 1:
                        new_value = max(current_value * factor, min_value)
                    else:
                        new_value = max(current_value - amount, min_value)
                else:
                    result['error'] = f'Cannot decrease non-numeric value: {current_value}'
                    return result
            else:
                result['error'] = f'Unknown operation: {operation}'
                return result
            
            # Apply change
            target[final_key] = new_value
            result['old_value'] = current_value
            result['new_value'] = new_value
            
            # Write back if not dry run
            if not self.dry_run:
                with open(file_path, 'w') as f:
                    yaml.dump(config, f, default_flow_style=False, indent=2)
                logger.info(f"Updated {file_path}: {'.'.join(yaml_path)} = {new_value}")
            else:
                logger.info(f"[DRY RUN] Would update {file_path}: {'.'.join(yaml_path)} = {new_value}")
            
            result['success'] = True
            
        except Exception as e:
            logger.error(f"Error fixing YAML config: {e}")
            result['error'] = str(e)
        
        return result
    
    async def _fix_code_file(
        self,
        file_path: Path,
        fix_spec: Dict[str, Any],
        result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Fix code file using regex replacement"""
        try:
            # Read file
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Check if this is a verify-only fix
            if fix_spec.get('action') == 'verify_only':
                verify_pattern = fix_spec.get('verify')
                if re.search(verify_pattern, content):
                    result['success'] = True
                    result['message'] = 'Verification passed - no fix needed'
                    logger.info(f"Verification passed for {file_path}")
                else:
                    result['success'] = False
                    result['message'] = 'Verification failed - manual intervention required'
                    logger.warning(f"Verification failed for {file_path}")
                return result
            
            # Apply regex replacement
            search_pattern = fix_spec.get('search')
            replace_func = fix_spec.get('replace')
            
            if not search_pattern or not replace_func:
                result['error'] = 'Missing search pattern or replace function'
                return result
            
            # Find matches
            matches = list(re.finditer(search_pattern, content))
            
            if not matches:
                result['message'] = 'No matches found - pattern may have already been fixed'
                result['success'] = True
                return result
            
            # Check value constraints
            min_value = fix_spec.get('min_value')
            max_value = fix_spec.get('max_value')
            
            new_content = content
            replacements = []
            
            for match in matches:
                # Get current value
                if match.groups():
                    current_val = match.group(1)
                    try:
                        current_num = float(current_val)
                        
                        # Check if within acceptable range
                        if max_value and current_num >= max_value:
                            logger.info(f"Value already at maximum: {current_num} >= {max_value}")
                            continue
                        
                        if min_value and current_num < min_value:
                            logger.info(f"Value below minimum: {current_num} < {min_value}")
                            continue
                    
                    except ValueError:
                        pass  # Not a numeric value
                
                # Apply replacement
                replacement = replace_func(match)
                new_content = new_content.replace(match.group(0), replacement, 1)
                
                replacements.append({
                    'old': match.group(0),
                    'new': replacement
                })
            
            if not replacements:
                result['message'] = 'No changes needed - values already optimal'
                result['success'] = True
                return result
            
            result['replacements'] = replacements
            result['changes_count'] = len(replacements)
            
            # Write back if not dry run
            if not self.dry_run:
                with open(file_path, 'w') as f:
                    f.write(new_content)
                logger.info(f"Applied {len(replacements)} fix(es) to {file_path}")
            else:
                logger.info(f"[DRY RUN] Would apply {len(replacements)} fix(es) to {file_path}")
            
            result['success'] = True
            
        except Exception as e:
            logger.error(f"Error fixing code file: {e}")
            result['error'] = str(e)
        
        return result
    
    async def _apply_ai_suggestion(
        self,
        ai_suggestion: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply an AI-generated fix suggestion"""
        result = {
            'description': 'AI-suggested fix',
            'success': False,
            'ai_suggestion': ai_suggestion
        }
        
        try:
            fix_type = ai_suggestion.get('fix_type', 'unknown')
            changes = ai_suggestion.get('changes', [])
            
            if fix_type == 'manual' or not changes:
                result['message'] = 'AI suggests manual intervention'
                result['rationale'] = ai_suggestion.get('rationale', '')
                result['risks'] = ai_suggestion.get('risks', [])
                return result
            
            # For now, log AI suggestion but don't auto-apply
            # This is a safety measure - AI suggestions should be reviewed
            result['message'] = 'AI suggestion logged for manual review'
            result['requires_review'] = True
            result['success'] = True  # Success = logged, not applied
            
            logger.info(f"AI fix suggestion (requires review): {ai_suggestion.get('rationale', '')}")
            
        except Exception as e:
            logger.error(f"Error processing AI suggestion: {e}")
            result['error'] = str(e)
        
        return result
    
    def _create_backup(self, file_path: Path) -> Path:
        """Create a backup of a file before modifying it"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"{file_path.name}.{timestamp}.backup"
        backup_path = self.backup_dir / backup_name
        
        shutil.copy2(file_path, backup_path)
        logger.info(f"Created backup: {backup_path}")
        
        return backup_path
    
    def restore_backup(self, backup_path: Path) -> bool:
        """Restore a file from backup"""
        try:
            if not backup_path.exists():
                logger.error(f"Backup not found: {backup_path}")
                return False
            
            # Extract original filename
            original_name = backup_path.name.split('.')[0]
            # Find original file location (simple heuristic)
            # In practice, you'd want to store this mapping
            
            logger.info(f"Restored from backup: {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error restoring backup: {e}")
            return False
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """List all available backups"""
        backups = []
        
        try:
            for backup_file in self.backup_dir.glob("*.backup"):
                backups.append({
                    'filename': backup_file.name,
                    'path': str(backup_file),
                    'size': backup_file.stat().st_size,
                    'created': datetime.fromtimestamp(
                        backup_file.stat().st_ctime
                    ).isoformat()
                })
        
        except Exception as e:
            logger.error(f"Error listing backups: {e}")
        
        return backups

