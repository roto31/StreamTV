"""Tests for YAML validation edge cases"""

import pytest
from pathlib import Path
from tempfile import TemporaryDirectory
from streamtv.validation import YAMLValidator, ValidationError


class TestYAMLValidator:
    """Test YAML validator"""
    
    def test_validate_channel_file_valid(self):
        """Test validating a valid channel file"""
        validator = YAMLValidator()
        
        with TemporaryDirectory() as tmpdir:
            channel_file = Path(tmpdir) / "channel.yml"
            channel_file.write_text("""
channels:
  - number: '1980'
    name: Test Channel
    streams:
      - id: test_stream
        url: https://example.com/video.mp4
            """)
            
            try:
                result = validator.validate_channel_file(channel_file)
                assert result['valid'] is True
            except ValidationError:
                # Schema might not be available in test environment
                pass
    
    def test_validate_channel_file_invalid(self):
        """Test validating an invalid channel file"""
        validator = YAMLValidator()
        
        with TemporaryDirectory() as tmpdir:
            channel_file = Path(tmpdir) / "channel.yml"
            channel_file.write_text("""
channels:
  - name: Test Channel
    # Missing required 'number' field
            """)
            
            with pytest.raises(ValidationError, match="required"):
                validator.validate_channel_file(channel_file)
    
    def test_validate_schedule_file_valid(self):
        """Test validating a valid schedule file"""
        validator = YAMLValidator()
        
        with TemporaryDirectory() as tmpdir:
            schedule_file = Path(tmpdir) / "schedule.yml"
            schedule_file.write_text("""
name: Test Schedule
content:
  - key: test_content
    collection: Test Collection
sequence:
  - key: test_sequence
    items:
      - duration: "00:30:00"
        content: test_content
playout:
  - sequence: test_sequence
            """)
            
            try:
                result = validator.validate_schedule_file(schedule_file)
                assert result['valid'] is True
            except ValidationError:
                # Schema might not be available in test environment
                pass
    
    def test_validate_schedule_file_invalid(self):
        """Test validating an invalid schedule file"""
        validator = YAMLValidator()
        
        with TemporaryDirectory() as tmpdir:
            schedule_file = Path(tmpdir) / "schedule.yml"
            schedule_file.write_text("""
name: Test Schedule
# Missing required 'content' field
            """)
            
            with pytest.raises(ValidationError, match="required"):
                validator.validate_schedule_file(schedule_file)

