import socket

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = socket.gethostbyname(socket.gethostname())
    finally:
        s.close()
    return IP

if __name__ == "__main__":
    ip = get_local_ip()
    print("=" * 56)
    print(f"On your phone (same Wi-Fi): http://{ip}:8501")
    print("=" * 56)
