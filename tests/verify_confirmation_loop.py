
import requests
import json
import time

API_URL = "http://localhost:8000"

def run_test():
    print("[TEST] Starting Research Request...")
    # 1. Start Research
    try:
        resp = requests.post(f"{API_URL}/api/research", json={"question": "Optimize LLM inference"})
        if resp.status_code != 200:
            print(f"[TEST] Failed to start research: {resp.text}")
            return
        
        session_id = resp.json()["session_id"]
        print(f"[TEST] Session ID: {session_id}")
    except Exception as e:
        print(f"[TEST] Error connecting to API: {e}")
        return

    # 2. Listen for Events
    url = f"{API_URL}/api/events/{session_id}"
    print(f"[TEST] Listening to events at {url}")
    
    state = "waiting_first_confirmation"
    
    try:
        with requests.get(url, stream=True) as response:
            for line in response.iter_lines():
                if line:
                    decoded_line = line.decode('utf-8')
                    if decoded_line.startswith("data:"):
                        data_str = decoded_line[5:].strip()
                        try:
                            data = json.loads(data_str)
                        except json.JSONDecodeError:
                            continue
                            
                        event_type = data.get("type")
                        
                        if event_type == "node_reasoning":
                            reasoning = data.get("reasoning", "")
                            print(f"[REASONING] {reasoning[:60]}...")
                            
                        elif event_type == "node_complete":
                             print(f"[NODE] Completed: {data.get('node')}")

                        elif event_type == "hitl_required":
                            payload = data.get('payload', {})
                            hitl_type = payload.get('type')
                            node = data.get('node')
                            
                            print(f"\n[HITL] Required at {node} (Type: {hitl_type})")
                            
                            if state == "waiting_first_confirmation":
                                if hitl_type == 'confirmation':
                                    print("[TEST] >>> 1st Confirmation Received.")
                                    print(f" > Intent: {payload.get('research_intent')}")
                                    print(f" > Question: {payload.get('normalized_question')}")
                                    
                                    # REFINE
                                    print("[TEST] Sending 'Refine' Action...")
                                    requests.post(f"{API_URL}/api/approve/{session_id}", json={
                                        "action": "refine",
                                        "feedback": "Focus specifically on INT8 quantization for Llama-3"
                                    })
                                    state = "waiting_second_confirmation"
                                else:
                                    print(f"[TEST] Unexpected HITL type: {hitl_type}")

                            elif state == "waiting_second_confirmation":
                                if hitl_type == 'confirmation':
                                    print("[TEST] >>> 2nd Confirmation Received.")
                                    q = payload.get('normalized_question')
                                    print(f" > New Question: {q}")
                                    
                                    if "INT8" in q or "Quantization" in str(payload) or "Llama-3" in str(payload):
                                        print("[TEST] SUCCESS: Refinement applied!")
                                    else:
                                        print("[TEST] WARNING: Refinement might not have been applied.")
                                    
                                    # APPROVE
                                    print("[TEST] Sending 'Approve' Action...")
                                    requests.post(f"{API_URL}/api/approve/{session_id}", json={"action": "approve"})
                                    state = "waiting_contract"
                                else:
                                      # Maybe it skipped straight to contract?
                                      print(f"[TEST] Unexpected HITL type: {hitl_type}")

                            elif state == "waiting_contract":
                                if hitl_type == 'approval':
                                    print("[TEST] >>> Contract Approval Received.")
                                    print(f" > Summary: {payload.get('contract_summary')[:50]}...")
                                    
                                    # APPROVE
                                    print("[TEST] Sending 'Approve' Contract...")
                                    requests.post(f"{API_URL}/api/approve/{session_id}", json={"action": "approve"})
                                    state = "running"
                                    
                        elif event_type == "complete":
                            print(f"\n[TEST] Research Complete! Verdict: {data.get('verdict')}")
                            return
                            
                        elif event_type == "error":
                            print(f"[TEST] API Error: {data.get('message')}")
                            return

    except KeyboardInterrupt:
        print("\n[TEST] Stopping...")
    except Exception as e:
        print(f"[TEST] Error: {e}")

if __name__ == "__main__":
    run_test()
