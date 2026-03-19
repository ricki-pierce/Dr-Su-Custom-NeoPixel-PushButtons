import socket
import time

AURORA_HOST = '127.0.0.1'
AURORA_PORT = 9000

def send_raw(message, label):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(2)
            sock.connect((AURORA_HOST, AURORA_PORT))
            sock.sendall(message)
            print(f"✓ Sent [{label}]: {repr(message)}")
    except Exception as e:
        print(f"✗ Failed [{label}]: {e}")

if __name__ == "__main__":
    print("Testing different trigger formats...\n")
    
    formats = [
        (b"1\n",                    "plain number newline"),
        (b"1\r\n",                  "plain number CRLF"),
        (b"TTL1\n",                 "TTL format"),
        (b"MARKER 1\n",             "MARKER space"),
        (b"MARKER=1\n",             "MARKER equals"),
        (b"trigger 1\n",            "trigger lowercase"),
        (b"TRIGGER 1\n",            "TRIGGER uppercase"),
        (b"\x01",                   "raw byte 0x01"),
        (b"stimulus=1\n",           "stimulus format"),
        (b'{"marker": 1}\n',        "JSON format"),
    ]
    
    for msg, label in formats:
        send_raw(msg, label)
        time.sleep(2)   # wait between each so you can see them individually in Aurora
    
    print("\nDone — check Aurora for any markers that appeared!")
