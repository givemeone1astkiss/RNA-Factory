#!/usr/bin/env python3
"""
RNA Model Integration Platform Main Run File
"""

import os
import sys
from app import create_app
from dotenv import load_dotenv


def main():
    """Main function"""
    load_dotenv()
    
    # Set environment variables
    os.environ.setdefault("FLASK_ENV", "development")

    # Create application instance
    app = create_app()

    # Run application
    print("Starting RNA Model Integration Platform...")
    print("Access URL: http://localhost:5000")
    print("Press Ctrl+C to stop service")

    try:
        app.run(host="0.0.0.0", port=5000, debug=True)
    except KeyboardInterrupt:
        print("\nService stopped")
    except Exception as e:
        print(f"Startup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
