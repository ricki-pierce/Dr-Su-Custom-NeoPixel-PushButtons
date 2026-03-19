import socket
import time

AURORA_HOST = '127.0.0.1'
AURORA_PORT = 9000          # ← correct port this time

def send_trigger(marker_value):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(2)
            sock.connect((AURORA_HOST, AURORA_PORT))
            message = f"{marker_value}\n"
            sock.sendall(message.encode('utf-8'))
            print(f"✓ Trigger sent: {marker_value}")
            return True
    except ConnectionRefusedError:
        print("✗ Connection refused")
        return False
    except socket.timeout:
        print("✗ Timed out")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

if __name__ == "__main__":
    send_trigger(1)
    time.sleep(2)
    send_trigger(2)
    time.sleep(2)
    send_trigger(0)
