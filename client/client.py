import socket
import ssl
import json
import sys

class RemoteExecutionClient:
    def __init__(self, host='localhost', port=9999):
        self.host = host
        self.port = port
        self.socket = None
        self.session_id = None
        self.ssl_context = self.create_ssl_context()
    
    def create_ssl_context(self):
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE  # For self-signed certs
        return context
    
    def connect(self):
        try:
            raw_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket = self.ssl_context.wrap_socket(
                raw_socket,
                server_hostname=self.host
            )
            self.socket.connect((self.host, self.port))
            print(f"[+] Secure connection established to {self.host}:{self.port}")
            print(f"[+] SSL/TLS encryption enabled\n")
            return True
        except Exception as e:
            print(f"[!] Connection failed: {e}")
            return False
    
    def authenticate(self, username, password):
        auth_request = {
            'type': 'AUTH',
            'username': username,
            'password': password
        }
        
        response = self.send_request(auth_request)
        
        if response and response.get('status') == 'SUCCESS':
            self.session_id = response.get('session_id')
            print(f"[+] {response.get('message')}")
            return True
        else:
            print(f"[!] Authentication failed: {response.get('message')}")
            return False
    
    def execute_command(self, command):
        if not self.session_id:
            print("[!] Not authenticated. Please login first.")
            return None
        
        cmd_request = {
            'type': 'COMMAND',
            'session_id': self.session_id,
            'command': command
        }
        
        response = self.send_request(cmd_request)
        return response
    
    def send_request(self, request):
        try:
            self.socket.send(json.dumps(request).encode())
            data = self.socket.recv(4096)
            return json.loads(data.decode())
        except Exception as e:
            print(f"[!] Communication error: {e}")
            return None
    
    def interactive_mode(self):
        print("\n" + "="*60)
        print("  Secure Remote Command Execution - Interactive Mode")
        print("="*60)
        print("\nCommands:")
        print("  - Type any allowed command to execute")
        print("  - 'help' - Show allowed commands")
        print("  - 'quit' or 'exit' - Disconnect\n")
        
        while True:
            try:
                command = input(f"remote> ").strip()
                
                if not command:
                    continue
                
                if command.lower() in ['quit', 'exit']:
                    print("[*] Disconnecting...")
                    break
                
                if command.lower() == 'help':
                    print("\nAllowed commands:")
                    print("  ls, pwd, whoami, date, echo, cat, uname, hostname")
                    print("  Example: ls -la")
                    print("  Example: echo 'Hello World'\n")
                    continue
                
                response = self.execute_command(command)
                
                if response:
                    if response.get('status') == 'SUCCESS':
                        print(f"\n{response.get('output')}")
                    else:
                        print(f"\n[!] Error: {response.get('output')}")
                
            except KeyboardInterrupt:
                print("\n[*] Interrupted. Disconnecting...")
                break
            except Exception as e:
                print(f"[!] Error: {e}")
    
    def close(self):
        if self.socket:
            self.socket.close()
            print("[*] Connection closed")

def main():
    print("="*60)
    print("  Secure Remote Command Execution Client")
    print("="*60)
    
    # Get server details
    host = input("\nEnter server IP [localhost]: ").strip() or 'localhost'
    port_input = input("Enter server port [9999]: ").strip()
    port = int(port_input) if port_input else 9999
    
    # Create client
    client = RemoteExecutionClient(host, port)
    
    # Connect
    if not client.connect():
        sys.exit(1)
    
    # Authenticate
    print("\n--- Authentication ---")
    print("Default users: admin/admin123, user1/password1, user2/password2\n")
    
    max_attempts = 3
    for attempt in range(max_attempts):
        username = input("Username: ").strip()
        password = input("Password: ").strip()
        
        if client.authenticate(username, password):
            break
        else:
            if attempt < max_attempts - 1:
                print(f"[!] Try again ({max_attempts - attempt - 1} attempts left)\n")
            else:
                print("[!] Maximum authentication attempts reached")
                client.close()
                sys.exit(1)
    
    # Interactive mode
    try:
        client.interactive_mode()
    finally:
        client.close()

if __name__ == "__main__":
    main()
