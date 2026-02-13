import socket
import ssl
import threading
import json
import hashlib
import uuid
import subprocess
import shlex
import logging
from datetime import datetime

class AuditLogger:
    def __init__(self, log_file='logs/audit.log'):
        self.logger = logging.getLogger('AuditLogger')
        self.logger.setLevel(logging.INFO)
        
        handler = logging.FileHandler(log_file)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
    
    def log_connection(self, address, username=None):
        self.logger.info(f"CONNECTION | {address} | User: {username}")
    
    def log_authentication(self, username, success):
        status = "SUCCESS" if success else "FAILED"
        self.logger.info(f"AUTH | {username} | {status}")
    
    def log_command(self, username, command, success):
        status = "SUCCESS" if success else "FAILED"
        self.logger.info(f"COMMAND | {username} | {command} | {status}")

class AuthenticationManager:
    def __init__(self):
        # Default users - username: password_hash
        self.users = {
            "admin": self.hash_password("admin123"),
            "user1": self.hash_password("password1"),
            "user2": self.hash_password("password2")
        }
        self.active_sessions = {}
    
    def hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()
    
    def authenticate(self, username, password):
        password_hash = self.hash_password(password)
        
        if username in self.users and self.users[username] == password_hash:
            session_id = str(uuid.uuid4())
            self.active_sessions[session_id] = username
            return True, session_id
        
        return False, None
    
    def validate_session(self, session_id):
        return session_id in self.active_sessions
    
    def get_username(self, session_id):
        return self.active_sessions.get(session_id)
    
    def logout(self, session_id):
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]

class CommandExecutor:
    # Whitelist of allowed commands for security
    ALLOWED_COMMANDS = ['ls', 'pwd', 'whoami', 'date', 'echo', 'cat', 'uname', 'hostname']
    
    def execute(self, command_string):
        try:
            parts = shlex.split(command_string)
            
            if not parts:
                return False, "Empty command"
            
            base_command = parts[0]
            if base_command not in self.ALLOWED_COMMANDS:
                return False, f"Command '{base_command}' not allowed. Allowed: {', '.join(self.ALLOWED_COMMANDS)}"
            
            result = subprocess.run(
                parts,
                capture_output=True,
                text=True,
                timeout=10,
                check=False
            )
            
            output = result.stdout if result.stdout else result.stderr
            return True, output if output else "Command executed successfully (no output)"
            
        except subprocess.TimeoutExpired:
            return False, "Command execution timeout"
        except Exception as e:
            return False, f"Execution error: {str(e)}"

class RemoteExecutionServer:
    def __init__(self, host='0.0.0.0', port=9999):
        self.host = host
        self.port = port
        self.server_socket = None
        self.ssl_context = self.create_ssl_context()
        self.auth_manager = AuthenticationManager()
        self.command_executor = CommandExecutor()
        self.audit_logger = AuditLogger()
        self.active_clients = 0
    
    def create_ssl_context(self):
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain('certs/server.crt', 'certs/server.key')
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        return context
    
    def start(self):
        raw_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        raw_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        raw_socket.bind((self.host, self.port))
        raw_socket.listen(5)
        
        print(f"[*] Secure Remote Execution Server")
        print(f"[*] Listening on {self.host}:{self.port}")
        print(f"[*] SSL/TLS enabled")
        print(f"[*] Waiting for connections...\n")
        
        try:
            while True:
                client_socket, address = raw_socket.accept()
                print(f"[+] New connection from {address}")
                
                try:
                    secure_socket = self.ssl_context.wrap_socket(client_socket, server_side=True)
                    self.active_clients += 1
                    print(f"[+] SSL handshake completed | Active clients: {self.active_clients}")
                    
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(secure_socket, address)
                    )
                    client_thread.daemon = True
                    client_thread.start()
                    
                except ssl.SSLError as e:
                    print(f"[!] SSL handshake failed with {address}: {e}")
                    client_socket.close()
                    
        except KeyboardInterrupt:
            print("\n[*] Server shutting down...")
        finally:
            raw_socket.close()
    
    def handle_client(self, client_socket, address):
        session_id = None
        username = None
        
        try:
            self.audit_logger.log_connection(address)
            
            while True:
                data = client_socket.recv(4096)
                if not data:
                    break
                
                try:
                    request = json.loads(data.decode())
                    response = self.process_request(request, session_id, username, address)
                    
                    # Update session info after authentication
                    if request.get('type') == 'AUTH' and response.get('status') == 'SUCCESS':
                        session_id = response.get('session_id')
                        username = request.get('username')
                    
                    client_socket.send(json.dumps(response).encode())
                    
                except json.JSONDecodeError:
                    error_response = {
                        'type': 'ERROR',
                        'status': 'ERROR',
                        'message': 'Invalid JSON format'
                    }
                    client_socket.send(json.dumps(error_response).encode())
                    
        except Exception as e:
            print(f"[!] Error handling client {address}: {e}")
        finally:
            if session_id:
                self.auth_manager.logout(session_id)
            client_socket.close()
            self.active_clients -= 1
            print(f"[-] Connection closed: {address} | Active clients: {self.active_clients}")
    
    def process_request(self, request, session_id, username, address):
        req_type = request.get('type')
        
        if req_type == 'AUTH':
            return self.handle_authentication(request)
        
        elif req_type == 'COMMAND':
            return self.handle_command(request, session_id, username)
        
        else:
            return {
                'type': 'ERROR',
                'status': 'ERROR',
                'message': 'Unknown request type'
            }
    
    def handle_authentication(self, request):
        username = request.get('username')
        password = request.get('password')
        
        success, session_id = self.auth_manager.authenticate(username, password)
        self.audit_logger.log_authentication(username, success)
        
        if success:
            return {
                'type': 'AUTH_RESPONSE',
                'status': 'SUCCESS',
                'session_id': session_id,
                'message': f'Welcome, {username}!'
            }
        else:
            return {
                'type': 'AUTH_RESPONSE',
                'status': 'FAILED',
                'message': 'Invalid username or password'
            }
    
    def handle_command(self, request, session_id, username):
        # Validate session
        if not session_id or not self.auth_manager.validate_session(session_id):
            return {
                'type': 'COMMAND_RESPONSE',
                'status': 'ERROR',
                'message': 'Not authenticated. Please login first.'
            }
        
        command = request.get('command')
        
        if not command:
            return {
                'type': 'COMMAND_RESPONSE',
                'status': 'ERROR',
                'message': 'No command provided'
            }
        
        # Execute command
        success, output = self.command_executor.execute(command)
        self.audit_logger.log_command(username, command, success)
        
        return {
            'type': 'COMMAND_RESPONSE',
            'status': 'SUCCESS' if success else 'ERROR',
            'output': output
        }

if __name__ == "__main__":
    server = RemoteExecutionServer()
    server.start()
