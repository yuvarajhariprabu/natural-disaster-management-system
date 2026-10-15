import urllib.request
import json
import time

def test_dshield_simulation():
    base_url = "http://localhost:8000/api"
    print("D-SHIELD: Running API & Risk Engine validation script...")
    
    # 1. Reset database to baseline
    req = urllib.request.Request(
        f"{base_url}/simulate",
        data=json.dumps({"scenario": "reset"}).encode(),
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            print("[-] Reset database status:", data["status"])
    except Exception as e:
        print("[X] FAIL: Database reset failed. Is the FastAPI backend running on port 8000?")
        print(f"    Error detail: {e}")
        return

    # 2. Verify baseline state is SAFE
    try:
        with urllib.request.urlopen(f"{base_url}/summary") as resp:
            summary = json.loads(resp.read().decode())
            print(f"[-] Baseline overall severity: {summary['severity']}")
            assert summary['severity'] == "SAFE"
            print("[+] PASS: Baseline state is SAFE.")
    except Exception as e:
        print(f"[X] FAIL: Failed to verify baseline state. Error: {e}")
        return

    # 3. Trigger combined critical event simulation
    req = urllib.request.Request(
        f"{base_url}/simulate",
        data=json.dumps({"scenario": "critical"}).encode(),
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            print(f"[-] Critical event simulation status: {data['status']}")
            print(f"    - Landslide Risk: {data['landslide_risk']}%")
            print(f"    - Flood Risk: {data['flood_risk']}%")
            print(f"    - Overall Risk: {data['overall_risk']}%")
            print(f"    - Severity: {data['severity']}")
            assert data['severity'] == "CRITICAL"
            print("[+] PASS: Critical warning state detected and validated.")
    except Exception as e:
        print(f"[X] FAIL: Failed critical event simulation. Error: {e}")
        return

    # 4. Check active alerts generated in DB
    try:
        with urllib.request.urlopen(f"{base_url}/summary") as resp:
            summary = json.loads(resp.read().decode())
            alerts = summary['active_alerts']
            print(f"[-] Found {len(alerts)} active unacknowledged threat alerts.")
            assert len(alerts) > 0
            first_alert_id = alerts[0]['id']
            print(f"[+] PASS: Active alerts generated in DB. Test alert ID: {first_alert_id}")
    except Exception as e:
        print(f"[X] FAIL: Alerts generation check failed. Error: {e}")
        return

    # 5. Acknowledge the alert via POST
    ack_req = urllib.request.Request(
        f"{base_url}/alerts/{first_alert_id}/acknowledge",
        data=b"" # empty body POST
    )
    try:
        with urllib.request.urlopen(ack_req) as resp:
            data = json.loads(resp.read().decode())
            print(f"[-] Acknowledging alert {first_alert_id}: {data['status']}")
            assert data['status'] == "success"
    except Exception as e:
        print(f"[X] FAIL: Alert acknowledgment request failed. Error: {e}")
        return

    # 6. Verify the acknowledged alert is hidden from active panel
    try:
        with urllib.request.urlopen(f"{base_url}/summary") as resp:
            summary = json.loads(resp.read().decode())
            active_ids = [a['id'] for a in summary['active_alerts']]
            assert first_alert_id not in active_ids
            print("[+] PASS: Acknowledged alert successfully cleared from dashboard panel.")
    except Exception as e:
        print(f"[X] FAIL: Acknowledgment verification failed. Error: {e}")
        return

    print("\n[SUCCESS] ALL D-SHIELD BACKEND API & RISK ENGINE TESTS PASSED!")

if __name__ == "__main__":
    test_dshield_simulation()
