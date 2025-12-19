[0.2.7] - 2025-12-19

## Added
- **Crash Dump Support**: Added support for kdump collected files and respective configuration, for both sosreports and support config.

## Fixes
- **UI: Navigation Tweaks**: Default page is always "Overview" tab; Clicking logo/title redirects to document root.

## Security Improvements
- **Jinja2**: Updated from 3.1.2 to 3.1.6
- **zipp**: Pinned to 3.19.1 to avoid vulnerability
- **gunicorn**: Updated from 21.2.0 to 23.0.0