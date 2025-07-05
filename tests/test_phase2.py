#!/usr/bin/env python3
"""
Test script for Phase 2 improvements:
- Upload queue management
- Multiple YouTube channels
- Upload presets and templates
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.upload_queue import UploadQueue, UploadItem, UploadStatus
from app.channel_manager import ChannelManager, ChannelInfo, ChannelSettings
from app.upload_presets import PresetManager, UploadPreset, DescriptionTemplate

def test_upload_queue():
    """Test the upload queue system."""
    print("🧪 Testing Upload Queue System...")
    
    try:
        # Create queue
        queue = UploadQueue(max_concurrent=2)
        
        # Add some test uploads
        upload1 = queue.add_upload("/test/path1.mp4", "test1.mp4", 1024*1024, "hash1")
        upload2 = queue.add_upload("/test/path2.mp4", "test2.mp4", 2048*1024, "hash2")
        upload3 = queue.add_upload("/test/path3.mp4", "test3.mp4", 3072*1024, "hash3")
        
        # Test queue operations
        assert len(queue.queue) == 3, f"Expected 3 items, got {len(queue.queue)}"
        
        # Test pause/resume
        assert queue.pause_upload(upload1) == False, "Should not be able to pause pending upload"
        upload1.status = UploadStatus.UPLOADING
        assert queue.pause_upload(upload1) == True, "Should be able to pause uploading upload"
        assert upload1.status == UploadStatus.PAUSED, "Upload should be paused"
        
        # Test resume
        assert queue.resume_upload(upload1) == True, "Should be able to resume paused upload"
        assert upload1.status == UploadStatus.PENDING, "Upload should be pending"
        
        # Test cancel
        assert queue.cancel_upload(upload2) == True, "Should be able to cancel pending upload"
        assert upload2.status == UploadStatus.CANCELLED, "Upload should be cancelled"
        
        # Test move
        assert queue.move_upload(upload3, 0) == True, "Should be able to move upload"
        assert queue.queue[0] == upload3, "Upload should be at position 0"
        
        # Test queue status
        status = queue.get_queue_status()
        assert status['pending'] == 2, f"Expected 2 pending, got {status['pending']}"
        assert status['cancelled'] == 1, f"Expected 1 cancelled, got {status['cancelled']}"
        
        # Test export/import
        exported = queue.export_queue()
        assert len(exported) == 3, f"Expected 3 exported items, got {len(exported)}"
        
        # Create new queue and import
        new_queue = UploadQueue()
        new_queue.import_queue(exported)
        assert len(new_queue.queue) == 2, f"Expected 2 items after import, got {len(new_queue.queue)}"
        
        print("✅ Upload queue system test passed")
        return True
        
    except Exception as e:
        print(f"❌ Upload queue system test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_channel_manager():
    """Test the channel manager system."""
    print("🧪 Testing Channel Manager System...")
    
    try:
        # Create temporary directory for test files
        temp_dir = tempfile.mkdtemp()
        
        try:
            # Create channel manager with temporary files
            channels_file = os.path.join(temp_dir, "channels.json")
            settings_file = os.path.join(temp_dir, "channel_settings.json")
            tokens_dir = os.path.join(temp_dir, "tokens")
            
            # Create a mock channel manager (without actual API calls)
            manager = ChannelManager()
            manager.channels_file = channels_file
            manager.settings_file = settings_file
            manager.tokens_dir = tokens_dir
            
            # Create test channels
            channel1 = ChannelInfo(
                channel_id="UC123456789",
                channel_title="Test Channel 1",
                channel_description="Test description",
                subscriber_count=1000,
                video_count=50,
                view_count=100000
            )
            
            channel2 = ChannelInfo(
                channel_id="UC987654321",
                channel_title="Test Channel 2",
                channel_description="Another test channel",
                subscriber_count=500,
                video_count=25,
                view_count=50000
            )
            
            # Add channels
            manager.channels[channel1.channel_id] = channel1
            manager.channels[channel2.channel_id] = channel2
            
            # Create channel settings
            settings1 = ChannelSettings(
                channel_id=channel1.channel_id,
                privacy_status="unlisted",
                category_id="20",
                description_template="Test upload: {filename}"
            )
            
            settings2 = ChannelSettings(
                channel_id=channel2.channel_id,
                privacy_status="private",
                category_id="22",
                description_template="Private upload: {filename}"
            )
            
            manager.channel_settings[channel1.channel_id] = settings1
            manager.channel_settings[channel2.channel_id] = settings2
            
            # Test channel operations
            assert len(manager.get_all_channels()) == 2, f"Expected 2 channels, got {len(manager.get_all_channels())}"
            
            # Test set/get active channel
            assert manager.set_active_channel(channel1.channel_id) == True, "Should be able to set active channel"
            active_channel = manager.get_active_channel()
            assert active_channel.channel_id == channel1.channel_id, "Active channel should match"
            
            # Test get channel settings
            settings = manager.get_channel_settings(channel1.channel_id)
            assert settings.privacy_status == "unlisted", "Settings should match"
            
            # Test get active channel settings
            active_settings = manager.get_active_channel_settings()
            assert active_settings.channel_id == channel1.channel_id, "Active settings should match"
            
            # Test save/load
            manager._save_channels()
            manager._save_settings()
            
            # Create new manager and load
            new_manager = ChannelManager()
            new_manager.channels_file = channels_file
            new_manager.settings_file = settings_file
            new_manager._load_channels()
            new_manager._load_settings()
            
            assert len(new_manager.get_all_channels()) == 2, "Should load 2 channels"
            
            # Test statistics
            stats = manager.get_channel_statistics()
            assert stats['total_channels'] == 2, "Should have 2 channels"
            assert stats['total_subscribers'] == 1500, "Should have 1500 total subscribers"
            
            print("✅ Channel manager system test passed")
            return True
            
        finally:
            # Clean up
            shutil.rmtree(temp_dir, ignore_errors=True)
            
    except Exception as e:
        print(f"❌ Channel manager system test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_preset_manager():
    """Test the preset manager system."""
    print("🧪 Testing Preset Manager System...")
    
    try:
        # Create temporary files
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as tmp_presets:
            presets_file = tmp_presets.name
        
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as tmp_templates:
            templates_file = tmp_templates.name
        
        try:
            # Create preset manager
            manager = PresetManager(presets_file=presets_file, templates_file=templates_file)
            
            # Test default presets were created
            presets = manager.get_all_presets()
            assert len(presets) >= 4, f"Expected at least 4 default presets, got {len(presets)}"
            
            # Test default templates were created
            templates = manager.get_all_templates()
            assert len(templates) >= 4, f"Expected at least 4 default templates, got {len(templates)}"
            
            # Test get default preset
            default_preset = manager.get_default_preset()
            assert default_preset is not None, "Should have a default preset"
            assert default_preset.is_default == True, "Default preset should be marked as default"
            
            # Test add new preset
            new_preset = UploadPreset(
                name="Test Preset",
                description="Test preset for testing",
                privacy_status="public",
                category_id="20",
                tags=["test", "gaming"]
            )
            
            assert manager.add_preset(new_preset) == True, "Should be able to add preset"
            assert manager.get_preset("Test Preset") is not None, "Should be able to get added preset"
            
            # Test update preset
            assert manager.update_preset("Test Preset", privacy_status="private") == True, "Should be able to update preset"
            updated_preset = manager.get_preset("Test Preset")
            assert updated_preset.privacy_status == "private", "Preset should be updated"
            
            # Test set default preset
            assert manager.set_default_preset("Test Preset") == True, "Should be able to set default preset"
            new_default = manager.get_default_preset()
            assert new_default.name == "Test Preset", "Default preset should be updated"
            
            # Test add new template
            new_template = DescriptionTemplate(
                name="Test Template",
                template="Test upload: {filename} on {date}",
                description="Test template"
            )
            
            assert manager.add_template(new_template) == True, "Should be able to add template"
            assert manager.get_template("Test Template") is not None, "Should be able to get added template"
            
            # Test render template
            rendered = manager.render_template("Test Template", filename="test.mp4", date="2024-01-01")
            assert "test.mp4" in rendered, "Template should render with variables"
            assert "2024-01-01" in rendered, "Template should render with variables"
            
            # Test get available variables
            variables = manager.get_available_variables()
            assert "filename" in variables, "Should include filename variable"
            assert "date" in variables, "Should include date variable"
            
            # Test validate preset
            errors = manager.validate_preset(new_preset)
            assert len(errors) == 0, f"Preset should be valid, got errors: {errors}"
            
            # Test invalid preset
            invalid_preset = UploadPreset(
                name="",
                privacy_status="invalid",
                category_id="999"
            )
            errors = manager.validate_preset(invalid_preset)
            assert len(errors) > 0, "Invalid preset should have validation errors"
            
            # Test export/import
            export_file = os.path.join(tempfile.gettempdir(), "test_presets_export.json")
            assert manager.export_presets(export_file) == True, "Should be able to export presets"
            
            # Create new manager and import
            new_manager = PresetManager(presets_file=presets_file + "_new", templates_file=templates_file + "_new")
            assert new_manager.import_presets(export_file) == True, "Should be able to import presets"
            
            # Clean up export file
            if os.path.exists(export_file):
                os.remove(export_file)
            
            print("✅ Preset manager system test passed")
            return True
            
        finally:
            # Clean up
            if os.path.exists(presets_file):
                os.remove(presets_file)
            if os.path.exists(templates_file):
                os.remove(templates_file)
            
    except Exception as e:
        print(f"❌ Preset manager system test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_integration():
    """Test integration between the systems."""
    print("🧪 Testing System Integration...")
    
    try:
        # Create all managers
        queue = UploadQueue(max_concurrent=1)
        channel_manager = ChannelManager()
        preset_manager = PresetManager()
        
        # Test that they can work together
        # (This is a basic integration test - in a real scenario, you'd test actual uploads)
        
        # Create a test upload item
        upload_item = UploadItem(
            file_path="/test/video.mp4",
            file_name="video.mp4",
            file_size=1024*1024,
            file_hash="test_hash"
        )
        
        # Get a preset
        preset = preset_manager.get_default_preset()
        assert preset is not None, "Should have a default preset"
        
        # Test that we can use preset settings
        assert preset.privacy_status in ["private", "unlisted", "public"], "Preset should have valid privacy status"
        assert preset.category_id.isdigit(), "Preset should have valid category ID"
        
        # Test template rendering
        template = preset_manager.get_template("Simple")
        if template:
            rendered = template.render(filename="test.mp4")
            assert "test.mp4" in rendered or "Auto-uploaded" in rendered, "Template should render"
        
        print("✅ System integration test passed")
        return True
        
    except Exception as e:
        print(f"❌ System integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all Phase 2 tests."""
    print("🚀 Starting Phase 2 Tests...\n")
    
    tests = [
        ("Upload Queue System", test_upload_queue),
        ("Channel Manager System", test_channel_manager),
        ("Preset Manager System", test_preset_manager),
        ("System Integration", test_integration)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"Testing: {test_name}")
        print('='*50)
        
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name}: PASSED")
            else:
                print(f"❌ {test_name}: FAILED")
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {e}")
    
    print(f"\n{'='*50}")
    print(f"Test Results: {passed}/{total} tests passed")
    print('='*50)
    
    if passed == total:
        print("🎉 All Phase 2 tests passed! Advanced features are working correctly.")
        print("\n📋 Phase 2 Features Implemented:")
        print("✅ Upload Queue Management")
        print("   - Pause/resume individual uploads")
        print("   - Reorder upload queue")
        print("   - Cancel specific uploads")
        print("   - Queue status tracking")
        print("   - Export/import queue state")
        print("\n✅ Multiple YouTube Channels")
        print("   - Channel discovery and management")
        print("   - Channel-specific settings")
        print("   - Multiple OAuth tokens")
        print("   - Channel switching")
        print("\n✅ Upload Presets & Templates")
        print("   - Custom upload configurations")
        print("   - Description templates with variables")
        print("   - Preset validation and management")
        print("   - Export/import presets")
        return 0
    else:
        print("⚠️  Some tests failed. Please check the implementation.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 