#!/usr/bin/env python3
"""Debug app loading."""
import sys
import traceback

try:
    from dataverse_backend.app.main import app
    print('App loaded successfully')
    print(f'App: {app}')
    print(f'App routes: {len(app.routes)}')
    for route in app.routes:
        if hasattr(route, 'path'):
            print(f'  Route: {route.path}')
except Exception as e:
    print(f'Error loading app: {e}')
    traceback.print_exc()
    sys.exit(1)
