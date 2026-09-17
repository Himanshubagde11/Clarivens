import os
import time
import requests

API_URL = "http://localhost:8000/api"
FILE_PATH = "clarivens_universal_analytics_test_250k.csv"

def print_header(title):
    print(f"\n{'='*50}\n{title}\n{'='*50}")

def test_agent_discovery():
    print_header("1. Testing AI Agent Discovery & Chat")
    
    # Create Session
    res = requests.post(f"{API_URL}/ai/session", json={"project_id": None})
    if res.status_code != 200:
        print(f"Failed to create session: {res.text}")
        return None
    session_id = res.json()["session_id"]
    print(f"Session Created: {session_id}")
    
    # Send Chat Message
    payload = {
        "session_id": session_id,
        "message": "I need help analyzing some financial data for predictive forecasting."
    }
    res = requests.post(f"{API_URL}/ai/chat", json=payload)
    if res.status_code == 200:
        data = res.json()
        print(f"Agent Reply: {data.get('response', '')[:100]}...")
        print(f"Detected Intent: {data.get('intent')}")
        print(f"New State: {data.get('state')}")
    else:
        print(f"Chat failed: {res.text}")

def test_project_and_pipeline():
    print_header("2. Testing Project Creation & Pipeline")
    
    # Create Project
    res = requests.post(f"{API_URL}/v1/projects", json={
        "name": "Test E2E Project",
        "description": "Automated test project"
    })
    
    if res.status_code != 200:
        print(f"Project creation failed: {res.text}")
        return
        
    project_id = res.json()["id"]
    print(f"Project Created: {project_id}")
    
    if not os.path.exists(FILE_PATH):
        # Create a dummy dataset if it doesn't exist
        with open(FILE_PATH, "w") as f:
            f.write("date,revenue,cost\n2022-01-01,1000,500\n2022-01-02,1200,600\n")
            
    # Upload Dataset
    print("Uploading dataset...")
    with open(FILE_PATH, "rb") as f:
        res = requests.post(
            f"{API_URL}/v1/projects/{project_id}/upload", 
            files={"file": f}
        )
        
    if res.status_code != 200:
        print(f"Upload failed: {res.text}")
        return
        
    print(f"Upload success: {res.json().get('dataset_id')}")
    
    # Poll for completion
    print("Polling for pipeline completion...")
    for i in range(15):
        time.sleep(2)
        res = requests.get(f"{API_URL}/v1/projects/{project_id}")
        data = res.json()
        status = data["project"]["status"]
        print(f"Status: {status}")
        
        if status in ["completed", "failed"]:
            break
            
    if status == "completed":
        results = data.get("results", [])
        print(f"\nPipeline SUCCESS! Found {len(results)} analysis artifacts:")
        for r in results:
            print(f"- {r.get('type')}")
    else:
        print("\nPipeline failed or timed out.")

if __name__ == "__main__":
    print("Starting E2E Verification...")
    test_agent_discovery()
    test_project_and_pipeline()
    print("\nVerification Complete.")
