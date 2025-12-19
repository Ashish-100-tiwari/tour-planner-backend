"""
Test script for Travel Agent functionality with Google Maps integration
"""
import requests
import json

# Configuration
BASE_URL = "http://localhost:8000"
TEST_EMAIL = "traveler@example.com"
TEST_PASSWORD = "travel123"
TEST_NAME = "Travel Tester"

def print_section(title):
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)

def signup_or_signin():
    """Sign up or sign in to get access token"""
    print_section("AUTHENTICATION")
    
    # Try signup first
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
        print("✓ New user created")
    elif response.status_code == 400:
        print("✓ User already exists")
    
    # Sign in
    response = requests.post(
        f"{BASE_URL}/auth/signin",
        json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        }
    )
    
    if response.status_code == 200:
        token = response.json()["access_token"]
        print(f"✓ Signed in successfully")
        return token
    else:
        print(f"✗ Signin failed: {response.status_code}")
        return None

def send_chat(token, message):
    """Send a chat message and print response"""
    response = requests.post(
        f"{BASE_URL}/v1/chat/completions",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "messages": [
                {"role": "user", "content": message}
            ],
            "temperature": 0.7,
            "max_tokens": 200
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        assistant_message = data["choices"][0]["message"]["content"]
        print(f"\n👤 User: {message}")
        print(f"🤖 Assistant: {assistant_message}\n")
        return assistant_message
    else:
        print(f"✗ Chat failed: {response.status_code}")
        print(response.text)
        return None

def test_travel_agent(token):
    """Test the travel agent functionality"""
    
    print_section("TEST 1: Greeting")
    send_chat(token, "Hello! I need help planning a trip")
    
    input("\nPress Enter to continue...")
    
    print_section("TEST 2: Journey Request (Simple)")
    send_chat(token, "I want to go from New York to Boston")
    
    input("\nPress Enter to continue...")
    
    print_section("TEST 3: Journey Request (Detailed)")
    send_chat(token, "I'm planning to travel from Los Angeles to San Francisco")
    
    input("\nPress Enter to continue...")
    
    print_section("TEST 4: International Journey")
    send_chat(token, "How do I get from London to Paris?")
    
    input("\nPress Enter to continue...")
    
    print_section("TEST 5: Follow-up Question")
    send_chat(token, "What's the best time to travel?")

def main():
    print("\n" + "="*70)
    print("  TRAVEL AGENT FEATURE TEST")
    print("="*70)
    print("\nThis test will verify:")
    print("  1. Travel agent system prompt is active")
    print("  2. Google Maps API integration works")
    print("  3. Journey information is retrieved and formatted")
    print("  4. LLM provides helpful travel summaries")
    
    # Authenticate
    token = signup_or_signin()
    if not token:
        print("\n✗ Authentication failed. Exiting.")
        return
    
    # Run tests
    test_travel_agent(token)
    
    print_section("TEST COMPLETE")
    print("\n✓ All tests completed!")
    print("\nVERIFY:")
    print("  - Did the assistant act as a travel agent?")
    print("  - Were journey details (distance, duration) provided?")
    print("  - Were the responses helpful and under 150 words?")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n\n✗ Error: {e}")
