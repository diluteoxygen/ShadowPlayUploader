#!/usr/bin/env python3
"""
Test script for the new profile dropdown UI.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.main_enhanced import EnhancedShadowPlayUploader
from app.logger import get_logger

logger = get_logger()

def test_profile_dropdown():
    """Test the profile dropdown functionality."""
    try:
        logger.info("Starting profile dropdown UI test...")
        
        # Create the enhanced GUI
        app = EnhancedShadowPlayUploader()
        
        # Test that the profile dropdown was created
        assert hasattr(app, 'profile_dropdown'), "Profile dropdown not created"
        assert app.profile_dropdown is not None, "Profile dropdown is None"
        
        # Test that the dropdown has the expected components
        dropdown = app.profile_dropdown
        assert hasattr(dropdown, 'profile_btn'), "Profile button not found"
        assert hasattr(dropdown, 'dropdown_win'), "Dropdown window not found"
        assert hasattr(dropdown, 'login_btn'), "Login button not found"
        assert hasattr(dropdown, 'logout_btn'), "Logout button not found"
        assert hasattr(dropdown, 'refresh_btn'), "Refresh button not found"
        
        # Test initial state
        assert dropdown.dropdown_open == False, "Dropdown should be closed initially"
        
        # Test that the dropdown can be shown/hidden
        dropdown._show_dropdown()
        assert dropdown.dropdown_open == True, "Dropdown should be open after show"
        assert dropdown.dropdown_win is not None, "Dropdown window should be created"
        
        dropdown._hide_dropdown()
        assert dropdown.dropdown_open == False, "Dropdown should be closed after hide"
        assert dropdown.dropdown_win is None, "Dropdown window should be destroyed"
        
        # Test state update
        dropdown.update_display()
        
        logger.info("✅ Profile dropdown UI test passed!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Profile dropdown UI test failed: {e}")
        return False

def test_gui_creation():
    """Test that the enhanced GUI creates successfully."""
    try:
        logger.info("Testing enhanced GUI creation...")
        
        # Create the enhanced GUI
        app = EnhancedShadowPlayUploader()
        
        # Test that all main components exist
        assert hasattr(app, 'app'), "Main window not created"
        assert hasattr(app, 'channel_manager'), "Channel manager not created"
        assert hasattr(app, 'preset_manager'), "Preset manager not created"
        assert hasattr(app, 'upload_queue'), "Upload queue not created"
        assert hasattr(app, 'profile_dropdown'), "Profile dropdown not created"
        
        # Test that the GUI components exist
        assert hasattr(app, 'channel_combobox'), "Channel combobox not found"
        assert hasattr(app, 'preset_combobox'), "Preset combobox not found"
        assert hasattr(app, 'folder_entry'), "Folder entry not found"
        assert hasattr(app, 'start_btn'), "Start button not found"
        assert hasattr(app, 'log_box'), "Log box not found"
        
        logger.info("✅ Enhanced GUI creation test passed!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Enhanced GUI creation test failed: {e}")
        return False

def main():
    """Run all UI tests."""
    logger.info("🧪 Starting UI Profile Dropdown Tests...")
    
    tests = [
        test_gui_creation,
        test_profile_dropdown,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    logger.info(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All UI tests passed!")
        return True
    else:
        logger.error("❌ Some UI tests failed!")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 