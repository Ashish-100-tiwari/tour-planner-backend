"""
Test script for conversation memory functionality
Run this after starting the server to verify the implementation
"""
import requests
import json
import time

# Configuration
BASE_URL = "http://localhost:8000"
TEST_EMAIL = "test@example.com"
TEST_PASSWORD = "testpassword123"
TEST_NAME = "Test User"

def print_section(title):
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)

def signup():
    """Sign up a test user"""
    print_section("1. SIGNUP TEST USER")
    
    response = requests.post(
        f"{BASE_URL}/auth/signup",
        json={
            "name": TEST_NAME,
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD,
            "confirm_password": TEST_PASSWORD
        }
    )
    
    if response.status_code == 201:
        print("✓ Signup successful")
        print(json.dumps(response.json(), indent=2))
        return True
    elif response.status_code == 400 and "already registered" in response.text:
        print("✓ User already exists (using existing account)")
        return True
    else:
        print(f"✗ Signup failed: {response.status_code}")
        print(response.text)
        return False

def signin():
    """Sign in and get access token"""
    print_section("2. SIGNIN AND GET TOKEN")
    
    response = requests.post(
        f"{BASE_URL}/auth/signin",
        json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        token = data["access_token"]
        print("✓ Signin successful")
        print(f"Token: {token[:50]}...")
        return token
    else:
        print(f"✗ Signin failed: {response.status_code}")
        print(response.text)
        return None

def send_chat_message(token, message):
    """Send a chat message"""
    response = requests.post(
        f"{BASE_URL}/v1/chat/completions",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "messages": [
                {"role": "user", "content": message}
            ],
            "temperature": 0.7,
            "max_tokens": 100
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        assistant_message = data["choices"][0]["message"]["content"]
        print(f"User: {message}")
        print(f"Assistant: {assistant_message}")
        return True
    else:
        print(f"✗ Chat failed: {response.status_code}")
        print(response.text)
        return False

def test_conversation_memory(token):
    """Test conversation memory with multiple messages"""
    print_section("3. TEST CONVERSATION MEMORY")
    
    print("\nSending first message...")
    send_chat_message(token, "My name is Alice. Remember this!")
    
    time.sleep(2)
    
    print("\nSending second message (should remember context)...")
    send_chat_message(token, "What is my name?")
    
    time.sleep(2)
    
    print("\nSending third message (should still remember)...")
    send_chat_message(token, "Can you tell me my name again?")

def clear_history(token):
    """Clear conversation history"""
    print_section("4. CLEAR CONVERSATION HISTORY")
    
    response = requests.delete(
        f"{BASE_URL}/v1/conversations/clear",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if response.status_code == 200:
        print("✓ Conversation history cleared")
        print(json.dumps(response.json(), indent=2))
        return True
    else:
        print(f"✗ Clear failed: {response.status_code}")
        print(response.text)
        return False

def test_after_clear(token):
    """Test that memory is cleared"""
    print_section("5. TEST AFTER CLEARING (should not remember)")
    
    print("\nSending message after clear...")
    send_chat_message(token, "What is my name?")

def main():
    print("\n" + "="*60)
    print("  CONVERSATION MEMORY TEST SUITE")
    print("="*60)
    
    # Step 1: Signup
    if not signup():
        print("\n✗ Test failed at signup")
        return
    
    # Step 2: Signin
    token = signin()
    if not token:
        print("\n✗ Test failed at signin")
        return
    
    # Step 3: Test conversation memory
    test_conversation_memory(token)
    
    # Step 4: Clear history
    time.sleep(2)
    clear_history(token)
    
    # Step 5: Test after clear
    time.sleep(2)
    test_after_clear(token)
    
    print_section("TEST COMPLETE")
    print("\n✓ All tests completed!")
    print("\nNOTE: Check if the assistant remembered your name in step 3")
    print("      and forgot it in step 5 to verify memory is working.")

if __name__ == "__main__":
    main()
