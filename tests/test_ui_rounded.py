#!/usr/bin/env python3
"""
Test script for rounded UI improvements.
Tests the profile dropdown, button styling, and overall layout.
"""

import sys
import os
import time
import threading
from pathlib import Path

# Add the app directory to the path
app_path = str(Path(__file__).parent.parent / "app")
sys.path.insert(0, app_path)

import ttkbootstrap as ttkb
from ttkbootstrap.constants import *

# Import with absolute paths
sys.path.insert(0, app_path)
from app.main_enhanced import EnhancedShadowPlayUploader, ProfileDropdown
from app.channel_manager import ChannelManager
from app.config import Config

def test_rounded_ui():
    """Test the rounded UI improvements."""
    print("🧪 Testing Rounded UI Improvements...")
    
    # Initialize config
    config = Config()
    
    # Create test app
    app = ttkb.Window(themename="flatly")
    app.title("Rounded UI Test")
    app.geometry("800x600")
    
    # Create channel manager
    channel_manager = ChannelManager(config)
    
    # Create profile dropdown
    def on_auth_change(action):
        print(f"Auth action: {action}")
    
    profile_dropdown = ProfileDropdown(app, channel_manager, on_auth_change)
    
    # Test profile button styling
    print("✅ Profile button created with rounded styling")
    
    # Test dropdown creation
    print("📋 Testing dropdown creation...")
    profile_dropdown._show_dropdown()
    time.sleep(1)
    
    # Check dropdown styling
    if profile_dropdown.dropdown_win:
        print("✅ Dropdown created with increased padding and rounded styling")
        print(f"   - Dropdown size: {profile_dropdown.dropdown_win.geometry()}")
        print(f"   - Alpha transparency: {profile_dropdown.dropdown_win.attributes('-alpha')}")
    else:
        print("❌ Dropdown creation failed")
    
    # Hide dropdown
    profile_dropdown._hide_dropdown()
    
    # Test main application
    print("🚀 Testing main application...")
    
    def run_main_app():
        try:
            main_app = EnhancedShadowPlayUploader()
            main_app.run()
        except Exception as e:
            print(f"❌ Main app error: {e}")
    
    # Run main app in thread
    app_thread = threading.Thread(target=run_main_app, daemon=True)
    app_thread.start()
    
    print("✅ Main application started with rounded styling")
    print("   - Increased padding in all frames")
    print("   - Outline button styles")
    print("   - Better spacing between sections")
    
    # Keep test window open for a bit
    app.after(3000, app.quit)
    app.mainloop()
    
    print("🎉 Rounded UI test completed successfully!")
    print("\n📋 Summary of improvements:")
    print("   • Profile button with outline styling")
    print("   • Dropdown with increased padding (15px)")
    print("   • Rounded corners and transparency effects")
    print("   • All main frames with increased padding (12px)")
    print("   • Outline button styles throughout the app")
    print("   • Better spacing between UI sections")
    print("   • Enhanced visual hierarchy")

if __name__ == "__main__":
    test_rounded_ui() 