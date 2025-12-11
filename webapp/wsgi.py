#!/usr/bin/env python3
"""WSGI entry point for production deployment"""

from webapp.app import create_app

application = create_app()

if __name__ == "__main__":
    application.run()
