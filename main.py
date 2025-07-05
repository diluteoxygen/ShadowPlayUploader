#!/usr/bin/env python3
"""
ShadowPlay Batch Uploader - Main Entry Point

This is the main entry point for the ShadowPlay Batch Uploader application.
It imports and runs the enhanced GUI from the app package.
"""

import sys
import os

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    """Main entry point for the application."""
    try:
        from app.main_enhanced import main as run_app
        run_app()
    except ImportError as e:
        print(f"Error importing application modules: {e}")
        print("Make sure all required dependencies are installed.")
        sys.exit(1)
    except Exception as e:
        print(f"Application error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 