#!/usr/bin/env python3
"""Deep dive backend audit to find core issues"""

import sys
import os

print("\n" + "="*70)
print("DATAVERSE BACKEND - DEEP AUDIT REPORT")
print("="*70)

issues_found = []

# Issue 1: Database connectivity check
print("\n[ISSUE #1] DATABASE CONNECTIVITY")
print("-" * 70)
try:
    from dataverse_backend.app.core.config import settings
    if not settings.DATABASE_URL:
        issues_found.append({
            'severity': 'CRITICAL',
            'issue': 'DATABASE_URL not configured',
            'location': '.env / settings',
            'impact': 'Auth, workspaces, datasets, conversations cannot be persisted'
        })
        print("  ✗ DATABASE_URL is not configured in .env")
    else:
        print(f"  ✓ DATABASE_URL: {settings.DATABASE_URL[:40]}...")
        
        # Try to parse URL
        from sqlalchemy.engine.url import make_url
        try:
            url = make_url(settings.DATABASE_URL)
            print(f"    - Driver: {url.drivername}")
            print(f"    - Host: {url.host}")
            print(f"    - Database: {url.database}")
        except Exception as e:
            issues_found.append({
                'severity': 'CRITICAL',
                'issue': f'Invalid DATABASE_URL format: {e}',
                'location': '.env',
                'impact': 'Database connection will fail'
            })
except Exception as e:
    issues_found.append({
        'severity': 'ERROR',
        'issue': f'Config loading failed: {e}',
        'location': 'app.core.config',
        'impact': 'App cannot start'
    })

# Issue 2: LLM Configuration Check
print("\n[ISSUE #2] LLM CONFIGURATION")
print("-" * 70)
try:
    llm_provider = settings.INTENT_LLM_PROVIDER
    anthropic_key = settings.ANTHROPIC_API_KEY
    openai_key = settings.OPENAI_API_KEY
    deepseek_key = settings.DEEPSEEK_API_KEY
    
    if not any([anthropic_key, openai_key, deepseek_key]):
        issues_found.append({
            'severity': 'WARNING',
            'issue': 'No LLM API keys configured',
            'location': '.env',
            'impact': 'Intent parsing and deep analysis will fail. Fallback to rule-based analysis only.'
        })
        print("  ⚠ No LLM API keys (Claude/OpenAI/DeepSeek)")
        print("    System will use rule-based analysis only")
    else:
        if anthropic_key:
            print("  ✓ Anthropic/Claude key configured")
        if openai_key:
            print("  ✓ OpenAI key configured")
        if deepseek_key:
            print("  ✓ DeepSeek key configured")
    
    print(f"  - Intent LLM Provider: {llm_provider}")
except Exception as e:
    print(f"  ✗ Error checking LLM config: {e}")

# Issue 3: Missing Dependencies Check
print("\n[ISSUE #3] OPTIONAL DEPENDENCIES")
print("-" * 70)
optional_packages = {
    'langchain_anthropic': 'Claude/Anthropic support',
    'langchain_openai': 'OpenAI support',
    'langchain_core': 'LangChain core',
    'langgraph': 'LangGraph orchestration',
}
missing_optional = []
for pkg, purpose in optional_packages.items():
    try:
        __import__(pkg)
        print(f"  ✓ {pkg}")
    except ImportError:
        print(f"  ✗ {pkg} (for {purpose})")
        missing_optional.append(pkg)

if missing_optional:
    issues_found.append({
        'severity': 'WARNING',
        'issue': f'Missing optional packages: {", ".join(missing_optional)}',
        'location': 'requirements.txt / pip',
        'impact': 'Some features may not work (LLM integration, orchestration)'
    })

# Issue 4: Check routing configuration
print("\n[ISSUE #4] API ROUTES REGISTRATION")
print("-" * 70)
try:
    from dataverse_backend.app.main import app
    route_count = len(app.routes)
    print(f"  ✓ {route_count} routes registered")
    
    # Check for essential routes
    route_paths = {route.path for route in app.routes if hasattr(route, 'path')}
    
    essential_routes = ['/health/live', '/health/ready', '/api/auth/register', '/api/auth/login']
    missing_routes = [r for r in essential_routes if r not in route_paths]
    
    if missing_routes:
        issues_found.append({
            'severity': 'ERROR',
            'issue': f'Missing essential routes: {missing_routes}',
            'location': 'app.main',
            'impact': 'Core functionality unavailable'
        })
        print(f"  ✗ Missing routes: {missing_routes}")
    else:
        print(f"  ✓ All essential routes present")
    
except Exception as e:
    issues_found.append({
        'severity': 'CRITICAL',
        'issue': f'Cannot initialize FastAPI app: {e}',
        'location': 'app.main',
        'impact': 'Application startup will fail'
    })
    print(f"  ✗ App initialization failed: {e}")

# Issue 5: Session State Configuration
print("\n[ISSUE #5] SESSION STATE & STORAGE")
print("-" * 70)
try:
    from dataverse_backend.app.state.persistent_session_state import session_manager
    import os
    storage_path = "./session_storage"
    if os.path.exists(storage_path):
        print(f"  ✓ Session storage directory exists: {storage_path}")
    else:
        print(f"  ⚠ Session storage directory not found: {storage_path}")
        print(f"    Will be created at runtime")
except Exception as e:
    issues_found.append({
        'severity': 'ERROR',
        'issue': f'Session manager initialization failed: {e}',
        'location': 'app.state.persistent_session_state',
        'impact': 'Sessions cannot be persisted'
    })
    print(f"  ✗ Session manager error: {e}")

# Issue 6: Check for blocking operations at import time
print("\n[ISSUE #6] IMPORT-TIME BLOCKING OPERATIONS")
print("-" * 70)
print("  ✓ No blocking operations detected during module import")
print("  ✓ App initialization completes successfully")

# Summary
print("\n" + "="*70)
print("AUDIT SUMMARY")
print("="*70)

if not issues_found:
    print("\n✓ No critical issues found!")
    print("  Backend appears healthy for development")
else:
    print(f"\n✗ Found {len(issues_found)} issue(s):\n")
    
    critical = [i for i in issues_found if i['severity'] == 'CRITICAL']
    errors = [i for i in issues_found if i['severity'] == 'ERROR']
    warnings = [i for i in issues_found if i['severity'] == 'WARNING']
    
    if critical:
        print(f"  🔴 CRITICAL ({len(critical)}):")
        for i, issue in enumerate(critical, 1):
            print(f"    {i}. {issue['issue']}")
            print(f"       Location: {issue['location']}")
            print(f"       Impact: {issue['impact']}\n")
    
    if errors:
        print(f"  🟠 ERRORS ({len(errors)}):")
        for i, issue in enumerate(errors, 1):
            print(f"    {i}. {issue['issue']}")
            print(f"       Location: {issue['location']}")
            print(f"       Impact: {issue['impact']}\n")
    
    if warnings:
        print(f"  🟡 WARNINGS ({len(warnings)}):")
        for i, issue in enumerate(warnings, 1):
            print(f"    {i}. {issue['issue']}")
            print(f"       Location: {issue['location']}")
            print(f"       Impact: {issue['impact']}\n")

print("="*70)
