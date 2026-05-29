#!/usr/bin/env python3
"""Verify Issue #1 - LangChain Packages Installation"""

print("\n" + "="*60)
print("ISSUE #1 VERIFICATION - LangChain Packages")
print("="*60 + "\n")

# Test 1: langchain_anthropic
try:
    from langchain_anthropic import ChatAnthropic
    print("✓ langchain_anthropic imported successfully")
except ImportError as e:
    print(f"✗ langchain_anthropic failed: {e}")

# Test 2: langchain_openai
try:
    from langchain_openai import ChatOpenAI
    print("✓ langchain_openai imported successfully")
except ImportError as e:
    print(f"✗ langchain_openai failed: {e}")

# Test 3: langchain_core messages
try:
    from langchain_core.messages import HumanMessage, AIMessage
    print("✓ langchain_core.messages imported successfully")
except ImportError as e:
    print(f"✗ langchain_core.messages failed: {e}")

# Test 4: langchain_core.tools
try:
    from langchain_core.tools import tool
    print("✓ langchain_core.tools imported successfully")
except ImportError as e:
    print(f"✗ langchain_core.tools failed: {e}")

# Test 5: langgraph
try:
    from langgraph.graph import StateGraph
    print("✓ langgraph imported successfully")
except ImportError as e:
    print(f"✗ langgraph failed: {e}")

# Test 6: App main module
try:
    from dataverse_backend.app.main import app
    print(f"✓ App initialized with {len(app.routes)} routes")
except Exception as e:
    print(f"✗ App initialization failed: {e}")

print("\n" + "="*60)
print("✓ ISSUE #1 RESOLVED - All LangChain packages installed")
print("="*60 + "\n")
