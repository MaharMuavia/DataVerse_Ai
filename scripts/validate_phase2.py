#!/usr/bin/env python3
"""End-to-end validation script for DataVerse Phase 2.

Validates:
- Database connectivity
- API health
- Authentication (login/register)
- Workspace management
- Dataset upload
- Conversation/messaging with streaming
"""

import asyncio
import httpx
import json
import sys
from datetime import datetime

BASE_URL = "http://localhost:8000"
API_URL = f"{BASE_URL}/api"

# Colors for console output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


async def print_section(title: str):
    """Print a section header."""
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}{title}{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")


async def print_success(message: str):
    """Print success message."""
    print(f"{GREEN}✓{RESET} {message}")


async def print_error(message: str):
    """Print error message."""
    print(f"{RED}✗{RESET} {message}")


async def print_info(message: str):
    """Print info message."""
    print(f"{YELLOW}→{RESET} {message}")


async def test_health_check():
    """Test API health check."""
    await print_section("Health Check")
    
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            response = await client.get(f"{API_URL}/health")
            if response.status_code == 200:
                data = response.json()
                await print_success("API is healthy")
                await print_info(f"Status: {data.get('status')}")
                return True
            else:
                await print_error(f"Health check failed: {response.status_code}")
                return False
        except Exception as e:
            await print_error(f"Could not connect to API: {e}")
            return False


async def test_auth(client: httpx.AsyncClient):
    """Test authentication flow."""
    await print_section("Authentication")
    
    # Register new user
    username = f"testuser_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    email = f"{username}@test.dataverse.ai"
    password = "TestPassword123!"
    
    await print_info(f"Registering user: {username}")
    
    try:
        register_response = await client.post(
            f"{API_URL}/auth/register",
            json={
                "username": username,
                "email": email,
                "full_name": "Test User",
                "password": password,
            }
        )
        
        if register_response.status_code != 201:
            await print_error(f"Registration failed: {register_response.status_code}")
            await print_info(f"Response: {register_response.text}")
            return None
        
        user_data = register_response.json()
        await print_success(f"User registered: {username}")
        await print_info(f"User ID: {user_data.get('id')}")
        
    except Exception as e:
        await print_error(f"Registration error: {e}")
        return None
    
    # Login
    await print_info("Logging in...")
    
    try:
        login_response = await client.post(
            f"{API_URL}/auth/login",
            data={
                "username": username,
                "password": password,
            }
        )
        
        if login_response.status_code != 200:
            await print_error(f"Login failed: {login_response.status_code}")
            return None
        
        token_data = login_response.json()
        token = token_data.get("access_token")
        
        await print_success("Login successful")
        await print_info(f"Token type: {token_data.get('token_type')}")
        
        return token
        
    except Exception as e:
        await print_error(f"Login error: {e}")
        return None


async def test_workspaces(client: httpx.AsyncClient, token: str):
    """Test workspace management."""
    await print_section("Workspace Management")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Create workspace
    await print_info("Creating workspace...")
    
    try:
        ws_response = await client.post(
            f"{API_URL}/workspaces/",
            headers=headers,
            json={
                "name": "Phase 2 Test Workspace",
                "description": "Testing workflow orchestration"
            }
        )
        
        if ws_response.status_code != 201:
            await print_error(f"Workspace creation failed: {ws_response.status_code}")
            return None
        
        workspace = ws_response.json()
        workspace_id = workspace.get("id")
        
        await print_success("Workspace created")
        await print_info(f"Workspace ID: {workspace_id}")
        
        return workspace_id
        
    except Exception as e:
        await print_error(f"Workspace error: {e}")
        return None


async def test_dataset_upload(client: httpx.AsyncClient, token: str, workspace_id: str):
    """Test dataset upload."""
    await print_section("Dataset Upload")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Create sample CSV
    csv_content = """product,sales,region,date
Widget A,1000,North,2025-01-01
Widget B,1500,South,2025-01-02
Widget C,2000,East,2025-01-03
Widget A,1200,West,2025-01-04
Widget B,1800,North,2025-01-05
"""
    
    await print_info("Uploading sample dataset...")
    
    try:
        files = {"file": ("sample_data.csv", csv_content.encode())}
        
        upload_response = await client.post(
            f"{API_URL}/workspaces/{workspace_id}/datasets/upload",
            headers=headers,
            files=files,
        )
        
        if upload_response.status_code != 202:
            await print_error(f"Upload failed: {upload_response.status_code}")
            await print_info(f"Response: {upload_response.text}")
            return None
        
        dataset = upload_response.json()
        dataset_id = dataset.get("id")
        
        await print_success("Dataset uploaded")
        await print_info(f"Dataset ID: {dataset_id}")
        await print_info(f"Status: {dataset.get('status')}")
        await print_info(f"Rows: {dataset.get('row_count')}, Cols: {dataset.get('col_count')}")
        
        return dataset_id
        
    except Exception as e:
        await print_error(f"Upload error: {e}")
        return None


async def test_conversation(client: httpx.AsyncClient, token: str, workspace_id: str, dataset_id: str):
    """Test conversation creation and messaging."""
    await print_section("Conversation & Messaging")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Create conversation
    await print_info("Creating conversation...")
    
    try:
        conv_response = await client.post(
            f"{API_URL}/workspaces/{workspace_id}/conversations",
            headers=headers,
            json={
                "dataset_id": dataset_id,
                "title": "Sales Analysis"
            }
        )
        
        if conv_response.status_code != 201:
            await print_error(f"Conversation creation failed: {conv_response.status_code}")
            return False
        
        conversation = conv_response.json()
        conversation_id = conversation.get("id")
        
        await print_success("Conversation created")
        await print_info(f"Conversation ID: {conversation_id}")
        
    except Exception as e:
        await print_error(f"Conversation error: {e}")
        return False
    
    # Send message with streaming
    await print_info("Sending message (streaming response)...")
    
    try:
        message_response = await client.post(
            f"{API_URL}/workspaces/{workspace_id}/conversations/{conversation_id}/messages",
            headers=headers,
            json={
                "content": "What are the top selling products?",
                "message_type": "text"
            },
            timeout=30,
        )
        
        if message_response.status_code != 200:
            await print_error(f"Message failed: {message_response.status_code}")
            return False
        
        # Process SSE stream
        event_count = 0
        async with client.stream(
            "POST",
            f"{API_URL}/workspaces/{workspace_id}/conversations/{conversation_id}/messages",
            headers=headers,
            json={
                "content": "What are the top selling products?",
                "message_type": "text"
            }
        ) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    try:
                        event_data = json.loads(line[6:])
                        event_type = event_data.get("type", "unknown")
                        event_count += 1
                        
                        await print_info(f"Event {event_count}: {event_type}")
                        
                        if event_type == "error":
                            await print_error(f"Agent error: {event_data.get('error')}")
                            
                    except json.JSONDecodeError:
                        pass
        
        if event_count > 0:
            await print_success(f"Received {event_count} streaming events")
            return True
        else:
            await print_error("No events received from stream")
            return False
            
    except Exception as e:
        await print_error(f"Streaming error: {e}")
        return False


async def main():
    """Run all validation tests."""
    
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}DataVerse Phase 2 - End-to-End Validation{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")
    print(f"Start time: {datetime.utcnow().isoformat()}")
    print(f"API Base: {API_URL}")
    
    # Test health
    if not await test_health_check():
        await print_error("API is not responding. Make sure backend is running:")
        await print_info("./setup.sh or setup.ps1")
        sys.exit(1)
    
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30) as client:
        # Test auth
        token = await test_auth(client)
        if not token:
            await print_error("Authentication failed")
            sys.exit(1)
        
        # Test workspaces
        workspace_id = await test_workspaces(client, token)
        if not workspace_id:
            await print_error("Workspace management failed")
            sys.exit(1)
        
        # Test dataset
        dataset_id = await test_dataset_upload(client, token, workspace_id)
        if not dataset_id:
            await print_error("Dataset upload failed")
            sys.exit(1)
        
        # Test conversation
        if not await test_conversation(client, token, workspace_id, dataset_id):
            await print_error("Conversation/messaging failed")
            sys.exit(1)
    
    # Summary
    await print_section("Validation Summary")
    await print_success("All Phase 2 components are working correctly!")
    print(f"\nNext steps:")
    print(f"  1. Start Celery workers: ./scripts/start-celery-workers.sh")
    print(f"  2. Access frontend: http://localhost:3000")
    print(f"  3. Login with test user")
    print(f"  4. Create workspace and upload data")
    print(f"  5. Chat with agent to analyze data")


if __name__ == "__main__":
    asyncio.run(main())
