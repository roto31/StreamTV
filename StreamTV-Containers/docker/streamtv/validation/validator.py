"""YAML file validation using JSON schemas"""

import yaml
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging
from jsonschema import validate, ValidationError as JSONSchemaValidationError, Draft7Validator
from jsonschema.exceptions import SchemaError

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Custom validation error with detailed message"""
    def __init__(self, message: str, errors: Optional[List[str]] = None):
        self.message = message
        self.errors = errors or []
        super().__init__(self.message)


class YAMLValidator:
    """Validate YAML files against JSON schemas"""
    
    def __init__(self):
        self.schemas = {}
        self._load_schemas()
    
    def _load_schemas(self):
        """Load JSON schemas from schemas directory"""
        schemas_dir = Path(__file__).parent.parent.parent / "schemas"
        
        if not schemas_dir.exists():
            logger.warning(f"Schemas directory not found: {schemas_dir}")
            return
        
        # Load channel schema
        channel_schema_path = schemas_dir / "channel.schema.json"
        if channel_schema_path.exists():
            with open(channel_schema_path, 'r') as f:
                self.schemas['channel'] = json.load(f)
            logger.info("Loaded channel schema")
        
        # Load schedule schema
        schedule_schema_path = schemas_dir / "schedule.schema.json"
        if schedule_schema_path.exists():
            with open(schedule_schema_path, 'r') as f:
                self.schemas['schedule'] = json.load(f)
            logger.info("Loaded schedule schema")
    
    def validate_channel_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Validate a channel YAML file
        
        Returns:
            Dict with 'valid' (bool) and 'errors' (list) keys
            
        Raises:
            ValidationError: If validation fails
        """
        if 'channel' not in self.schemas:
            raise ValidationError("Channel schema not loaded")
        
        return self._validate_file(file_path, self.schemas['channel'], 'channel')
    
    def validate_schedule_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Validate a schedule YAML file
        
        Returns:
            Dict with 'valid' (bool) and 'errors' (list) keys
            
        Raises:
            ValidationError: If validation fails
        """
        if 'schedule' not in self.schemas:
            raise ValidationError("Schedule schema not loaded")
        
        return self._validate_file(file_path, self.schemas['schedule'], 'schedule')
    
    def _validate_file(self, file_path: Path, schema: Dict[str, Any], schema_type: str) -> Dict[str, Any]:
        """Validate a YAML file against a schema"""
        if not file_path.exists():
            raise ValidationError(f"File not found: {file_path}")
        
        try:
            # Load and parse YAML
            with open(file_path, 'r') as f:
                yaml_data = yaml.safe_load(f)
            
            if yaml_data is None:
                raise ValidationError(f"Empty or invalid YAML file: {file_path}")
            
            # Convert Python date objects to strings for validation (YAML parser converts dates)
            yaml_data = self._normalize_data(yaml_data)
            
            # Validate against schema
            errors = []
            validator = Draft7Validator(schema)
            
            for error in validator.iter_errors(yaml_data):
                error_path = " -> ".join(str(p) for p in error.path)
                error_msg = f"{error_path}: {error.message}"
                errors.append(error_msg)
                logger.debug(f"Validation error: {error_msg}")
            
            if errors:
                error_message = f"Validation failed for {file_path.name} ({schema_type}):\n" + "\n".join(f"  - {e}" for e in errors)
                raise ValidationError(error_message, errors)
            
            logger.info(f"✓ Validated {file_path.name} ({schema_type})")
            return {
                'valid': True,
                'errors': [],
                'data': yaml_data
            }
            
        except yaml.YAMLError as e:
            raise ValidationError(f"YAML parsing error in {file_path.name}: {str(e)}")
        except JSONSchemaValidationError as e:
            raise ValidationError(f"Schema validation error in {file_path.name}: {str(e)}")
        except Exception as e:
            raise ValidationError(f"Unexpected error validating {file_path.name}: {str(e)}")
    
    def _normalize_data(self, data: Any) -> Any:
        """Normalize YAML data for JSON schema validation (convert dates, etc.)"""
        from datetime import date, datetime
        
        if isinstance(data, dict):
            return {k: self._normalize_data(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._normalize_data(item) for item in data]
        elif isinstance(data, (date, datetime)):
            # Convert date/datetime to ISO format string
            return data.isoformat()
        else:
            return data
    
    def validate_channel_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate channel data (already parsed YAML)"""
        if 'channel' not in self.schemas:
            raise ValidationError("Channel schema not loaded")
        
        errors = []
        validator = Draft7Validator(self.schemas['channel'])
        
        for error in validator.iter_errors(data):
            error_path = " -> ".join(str(p) for p in error.path)
            errors.append(f"{error_path}: {error.message}")
        
        if errors:
            raise ValidationError("Channel data validation failed", errors)
        
        return {'valid': True, 'errors': []}
    
    def validate_schedule_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate schedule data (already parsed YAML)"""
        if 'schedule' not in self.schemas:
            raise ValidationError("Schedule schema not loaded")
        
        errors = []
        validator = Draft7Validator(self.schemas['schedule'])
        
        for error in validator.iter_errors(data):
            error_path = " -> ".join(str(p) for p in error.path)
            errors.append(f"{error_path}: {error.message}")
        
        if errors:
            raise ValidationError("Schedule data validation failed", errors)
        
        return {'valid': True, 'errors': []}

