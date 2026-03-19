import socket
import time

# ── Configuration ──────────────────────────────────────────────
AURORA_HOST = '127.0.0.1'   # Aurora is on the same computer
AURORA_PORT = 5060

# ── Core trigger function ───────────────────────────────────────
def send_trigger(marker_value):
    """
    Send a trigger marker to Aurora fNIRS via TCP socket.
    marker_value: an integer (e.g. 1, 2, 3) representing your event code
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(2)  # 2 second timeout
            sock.connect((AURORA_HOST, AURORA_PORT))
            
            # Try sending as a simple number string with newline
            message = f"{marker_value}\n"
            sock.sendall(message.encode('utf-8'))
            
            print(f"✓ Trigger sent: {marker_value}")
            return True

    except ConnectionRefusedError:
        print("✗ Connection refused — is Aurora open and recording?")
        return False
    except socket.timeout:
        print("✗ Connection timed out")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

# ── Test run ────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Sending test triggers to Aurora...\n")
    
    send_trigger(1)    # e.g. stimulus onset
    time.sleep(2)
    
    send_trigger(2)    # e.g. different condition
    time.sleep(2)
    
    send_trigger(0)    # e.g. offset / reset
    
    print("\nDone.")
