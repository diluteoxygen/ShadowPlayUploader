import os
import sys
import time
import threading

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.channel_manager import ChannelManager
from app.upload_queue import UploadQueue
from app.upload_presets import PresetManager

def test_auth_and_channel_discovery():
    print("\U0001F9EA Testing authentication and channel discovery...")
    manager = ChannelManager()
    try:
        channels = manager.discover_channels()
        assert len(channels) > 0, "No channels discovered"
        print(f"\u2705 Discovered {len(channels)} channel(s): {[c.channel_title for c in channels]}")
        return True
    except Exception as e:
        print(f"\u274C Authentication/channel discovery failed: {e}")
        return False

def test_upload_queue():
    print("\U0001F9EA Testing upload queue initialization...")
    try:
        queue = UploadQueue(max_concurrent=1)
        assert hasattr(queue, 'queue'), "Queue attribute missing"
        print("\u2705 Upload queue initialized")
        return True
    except Exception as e:
        print(f"\u274C Upload queue test failed: {e}")
        return False

def test_presets():
    print("\U0001F9EA Testing preset/template loading...")
    try:
        presets = PresetManager()
        assert len(presets.presets) > 0, "No presets loaded"
        assert len(presets.templates) > 0, "No templates loaded"
        print(f"\u2705 Loaded {len(presets.presets)} presets and {len(presets.templates)} templates")
        return True
    except Exception as e:
        print(f"\u274C Preset/template test failed: {e}")
        return False

def main():
    results = [
        test_auth_and_channel_discovery(),
        test_upload_queue(),
        test_presets()
    ]
    print("\n=== Phase 3 Test Results ===")
    print(f"Passed: {results.count(True)}/{len(results)}")

if __name__ == "__main__":
    main() 