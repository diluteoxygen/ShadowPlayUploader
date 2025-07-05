import json
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path

from .logger import get_logger
from .config import get_config

logger = get_logger()
config = get_config()

@dataclass
class UploadPreset:
    """Represents an upload preset configuration."""
    name: str
    description: str = ""
    privacy_status: str = "unlisted"
    category_id: str = "20"
    description_template: str = "Auto-uploaded ShadowPlay clip"
    tags: List[str] = None
    playlist_id: Optional[str] = None
    auto_delete: bool = True
    move_instead_of_delete: bool = False
    uploaded_folder: str = "uploaded"
    chunk_size_mb: int = 1
    max_retries: int = 3
    retry_delay: int = 2
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    is_default: bool = False
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        # Convert datetime objects to ISO strings
        if self.created_at:
            data['created_at'] = self.created_at.isoformat()
        if self.updated_at:
            data['updated_at'] = self.updated_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UploadPreset':
        """Create from dictionary."""
        # Convert ISO strings back to datetime objects
        if 'created_at' in data and data['created_at']:
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if 'updated_at' in data and data['updated_at']:
            data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        return cls(**data)
    
    def update(self, **kwargs):
        """Update preset with new values."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.updated_at = datetime.now()

@dataclass
class DescriptionTemplate:
    """Represents a description template with variables."""
    name: str
    template: str
    description: str = ""
    variables: List[str] = None
    created_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.variables is None:
            self.variables = self._extract_variables()
        if self.created_at is None:
            self.created_at = datetime.now()
    
    def _extract_variables(self) -> List[str]:
        """Extract variable names from template (e.g., {filename}, {date})."""
        import re
        variables = re.findall(r'\{(\w+)\}', self.template)
        return list(set(variables))  # Remove duplicates
    
    def render(self, **kwargs) -> str:
        """Render template with provided variables."""
        try:
            return self.template.format(**kwargs)
        except KeyError as e:
            logger.warning(f"Missing variable in template: {e}")
            # Replace missing variables with empty string
            return self.template.format(**{k: kwargs.get(k, '') for k in self.variables})
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        if self.created_at:
            data['created_at'] = self.created_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DescriptionTemplate':
        """Create from dictionary."""
        if 'created_at' in data and data['created_at']:
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        return cls(**data)

class PresetManager:
    """Manages upload presets and templates."""
    
    def __init__(self, presets_file: str = "resources/upload_presets.json", templates_file: str = "resources/description_templates.json"):
        """
        Initialize the preset manager.
        
        Args:
            presets_file: Path to presets file
            templates_file: Path to templates file
        """
        self.presets_file = presets_file
        self.templates_file = templates_file
        self.presets: Dict[str, UploadPreset] = {}
        self.templates: Dict[str, DescriptionTemplate] = {}
        
        # Load existing data
        self._load_presets()
        self._load_templates()
        
        # Create default presets if none exist
        if not self.presets:
            self._create_default_presets()
        
        # Create default templates if none exist
        if not self.templates:
            self._create_default_templates()
        
        logger.info("Preset manager initialized")
    
    def _load_presets(self):
        """Load presets from file."""
        try:
            if os.path.exists(self.presets_file):
                with open(self.presets_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.presets = {
                        name: UploadPreset.from_dict(preset_data)
                        for name, preset_data in data.items()
                    }
                logger.info(f"Loaded {len(self.presets)} presets from {self.presets_file}")
        except Exception as e:
            logger.warning(f"Failed to load presets: {e}")
    
    def _save_presets(self):
        """Save presets to file."""
        try:
            data = {
                name: preset.to_dict()
                for name, preset in self.presets.items()
            }
            with open(self.presets_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.debug(f"Saved {len(self.presets)} presets to {self.presets_file}")
        except Exception as e:
            logger.error(f"Failed to save presets: {e}")
    
    def _load_templates(self):
        """Load templates from file."""
        try:
            if os.path.exists(self.templates_file):
                with open(self.templates_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.templates = {
                        name: DescriptionTemplate.from_dict(template_data)
                        for name, template_data in data.items()
                    }
                logger.info(f"Loaded {len(self.templates)} templates from {self.templates_file}")
        except Exception as e:
            logger.warning(f"Failed to load templates: {e}")
    
    def _save_templates(self):
        """Save templates to file."""
        try:
            data = {
                name: template.to_dict()
                for name, template in self.templates.items()
            }
            with open(self.templates_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.debug(f"Saved {len(self.templates)} templates to {self.templates_file}")
        except Exception as e:
            logger.error(f"Failed to save templates: {e}")
    
    def _create_default_presets(self):
        """Create default upload presets."""
        default_presets = [
            UploadPreset(
                name="Default",
                description="Default upload settings",
                privacy_status="unlisted",
                category_id="20",
                description_template="Auto-uploaded ShadowPlay clip",
                tags=["gaming", "shadowplay"],
                auto_delete=True,
                is_default=True
            ),
            UploadPreset(
                name="Private Archive",
                description="Upload videos as private for archiving",
                privacy_status="private",
                category_id="20",
                description_template="Archived ShadowPlay clip - {filename}",
                tags=["archive", "gaming"],
                auto_delete=False,
                move_instead_of_delete=True,
                uploaded_folder="archived"
            ),
            UploadPreset(
                name="Public Gaming",
                description="Upload gaming videos as public",
                privacy_status="public",
                category_id="20",
                description_template="Gaming clip: {filename}\n\nRecorded with NVIDIA ShadowPlay",
                tags=["gaming", "gameplay", "shadowplay"],
                auto_delete=True
            ),
            UploadPreset(
                name="High Quality",
                description="High quality uploads with larger chunk size",
                privacy_status="unlisted",
                category_id="20",
                description_template="High quality ShadowPlay clip",
                tags=["gaming", "hq"],
                chunk_size_mb=5,
                max_retries=5,
                retry_delay=3
            )
        ]
        
        for preset in default_presets:
            self.presets[preset.name] = preset
        
        self._save_presets()
        logger.info("Created default presets")
    
    def _create_default_templates(self):
        """Create default description templates."""
        default_templates = [
            DescriptionTemplate(
                name="Simple",
                template="Auto-uploaded ShadowPlay clip",
                description="Simple template with no variables"
            ),
            DescriptionTemplate(
                name="Detailed",
                template="ShadowPlay clip: {filename}\n\nRecorded on {date}\nFile size: {filesize_mb:.1f} MB",
                description="Detailed template with filename, date, and file size"
            ),
            DescriptionTemplate(
                name="Gaming",
                template="Gaming clip: {filename}\n\nRecorded with NVIDIA ShadowPlay\nGame: {game_name}\nDuration: {duration}",
                description="Gaming-focused template with game name and duration"
            ),
            DescriptionTemplate(
                name="Archive",
                template="Archived ShadowPlay clip\n\nFilename: {filename}\nDate: {date}\nSize: {filesize_mb:.1f} MB\nHash: {file_hash}",
                description="Archive template with detailed file information"
            )
        ]
        
        for template in default_templates:
            self.templates[template.name] = template
        
        self._save_templates()
        logger.info("Created default templates")
    
    def add_preset(self, preset: UploadPreset) -> bool:
        """Add a new preset."""
        try:
            # Ensure only one default preset
            if preset.is_default:
                for existing_preset in self.presets.values():
                    existing_preset.is_default = False
            
            self.presets[preset.name] = preset
            self._save_presets()
            logger.info(f"Added preset: {preset.name}")
            return True
        except Exception as e:
            logger.error(f"Failed to add preset {preset.name}: {e}")
            return False
    
    def get_preset(self, name: str) -> Optional[UploadPreset]:
        """Get a preset by name."""
        return self.presets.get(name)
    
    def get_default_preset(self) -> Optional[UploadPreset]:
        """Get the default preset."""
        for preset in self.presets.values():
            if preset.is_default:
                return preset
        return None
    
    def get_all_presets(self) -> List[UploadPreset]:
        """Get all presets."""
        return list(self.presets.values())
    
    def update_preset(self, name: str, **kwargs) -> bool:
        """Update an existing preset."""
        preset = self.presets.get(name)
        if preset:
            preset.update(**kwargs)
            self._save_presets()
            logger.info(f"Updated preset: {name}")
            return True
        return False
    
    def delete_preset(self, name: str) -> bool:
        """Delete a preset."""
        if name in self.presets:
            preset = self.presets[name]
            if preset.is_default:
                logger.warning(f"Cannot delete default preset: {name}")
                return False
            
            del self.presets[name]
            self._save_presets()
            logger.info(f"Deleted preset: {name}")
            return True
        return False
    
    def set_default_preset(self, name: str) -> bool:
        """Set a preset as default."""
        preset = self.presets.get(name)
        if preset:
            # Remove default from all other presets
            for existing_preset in self.presets.values():
                existing_preset.is_default = False
            
            # Set this preset as default
            preset.is_default = True
            self._save_presets()
            logger.info(f"Set default preset: {name}")
            return True
        return False
    
    def add_template(self, template: DescriptionTemplate) -> bool:
        """Add a new template."""
        try:
            self.templates[template.name] = template
            self._save_templates()
            logger.info(f"Added template: {template.name}")
            return True
        except Exception as e:
            logger.error(f"Failed to add template {template.name}: {e}")
            return False
    
    def get_template(self, name: str) -> Optional[DescriptionTemplate]:
        """Get a template by name."""
        return self.templates.get(name)
    
    def get_all_templates(self) -> List[DescriptionTemplate]:
        """Get all templates."""
        return list(self.templates.values())
    
    def delete_template(self, name: str) -> bool:
        """Delete a template."""
        if name in self.templates:
            del self.templates[name]
            self._save_templates()
            logger.info(f"Deleted template: {name}")
            return True
        return False
    
    def render_template(self, template_name: str, **kwargs) -> str:
        """Render a template with provided variables."""
        template = self.templates.get(template_name)
        if template:
            return template.render(**kwargs)
        else:
            logger.warning(f"Template not found: {template_name}")
            return kwargs.get('filename', 'Unknown file')
    
    def get_available_variables(self) -> List[str]:
        """Get list of all available template variables."""
        variables = set()
        for template in self.templates.values():
            variables.update(template.variables)
        return sorted(list(variables))
    
    def validate_preset(self, preset: UploadPreset) -> List[str]:
        """Validate a preset and return list of errors."""
        errors = []
        
        if not preset.name:
            errors.append("Preset name is required")
        
        if preset.privacy_status not in ["private", "unlisted", "public"]:
            errors.append("Invalid privacy status")
        
        if preset.category_id not in ["1", "2", "10", "15", "17", "19", "20", "22", "23", "24", "25", "26", "27", "28", "29"]:
            errors.append("Invalid category ID")
        
        if preset.chunk_size_mb <= 0:
            errors.append("Chunk size must be positive")
        
        if preset.max_retries < 0:
            errors.append("Max retries cannot be negative")
        
        return errors
    
    def export_presets(self, file_path: str) -> bool:
        """Export presets to a file."""
        try:
            data = {
                name: preset.to_dict()
                for name, preset in self.presets.items()
            }
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info(f"Exported {len(self.presets)} presets to {file_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to export presets: {e}")
            return False
    
    def import_presets(self, file_path: str) -> bool:
        """Import presets from a file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            imported_count = 0
            for name, preset_data in data.items():
                try:
                    preset = UploadPreset.from_dict(preset_data)
                    # Validate preset
                    errors = self.validate_preset(preset)
                    if errors:
                        logger.warning(f"Skipping invalid preset {name}: {errors}")
                        continue
                    
                    self.presets[name] = preset
                    imported_count += 1
                except Exception as e:
                    logger.warning(f"Failed to import preset {name}: {e}")
            
            self._save_presets()
            logger.info(f"Imported {imported_count} presets from {file_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to import presets: {e}")
            return False 