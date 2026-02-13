import time
import threading
import statistics
from client.client import RemoteExecutionClient

class PerformanceTest:
    def __init__(self, host='localhost', port=9999):
        self.host = host
        self.port = port
        self.results = []
        
    def single_client_test(self, client_id, num_commands=10):
        """Test single client performance"""
        result = {
            'client_id': client_id,
            'connection_time': 0,
            'auth_time': 0,
            'command_times': [],
            'total_time': 0,
            'success': False,
            'errors': []
        }
        
        try:
            start_total = time.time()
            
            # Test connection time
            client = RemoteExecutionClient(self.host, self.port)
            conn_start = time.time()
            if not client.connect():
                raise Exception("Connection failed")
            result['connection_time'] = time.time() - conn_start
            
            # Test authentication time
            auth_start = time.time()
            if not client.authenticate("admin", "admin123"):
                raise Exception("Authentication failed")
            result['auth_time'] = time.time() - auth_start
            
            # Test command execution times
            test_commands = ['pwd', 'whoami', 'date', 'ls', 'hostname']
            
            for i in range(num_commands):
                cmd = test_commands[i % len(test_commands)]
                cmd_start = time.time()
                response = client.execute_command(cmd)
                cmd_time = time.time() - cmd_start
                
                if response and response.get('status') == 'SUCCESS':
                    result['command_times'].append(cmd_time)
                else:
                    result['errors'].append(f"Command {cmd} failed")
            
            result['total_time'] = time.time() - start_total
            result['success'] = True
            
            client.close()
            
        except Exception as e:
            result['errors'].append(str(e))
        
        return result
    
    def concurrent_clients_test(self, num_clients, commands_per_client=10):
        """Test multiple concurrent clients"""
        print(f"\n{'='*60}")
        print(f"Testing {num_clients} concurrent clients")
        print(f"Commands per client: {commands_per_client}")
        print(f"{'='*60}")
        
        threads = []
        results = []
        
        start_time = time.time()
        
        # Create and start threads
        for i in range(num_clients):
            thread = threading.Thread(
                target=lambda id: results.append(
                    self.single_client_test(id, commands_per_client)
                ),
                args=(i,)
            )
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        total_time = time.time() - start_time
        
        # Analyze results
        self.analyze_results(results, num_clients, total_time)
        
        return results
    
    def analyze_results(self, results, num_clients, total_time):
        """Analyze and display performance metrics"""
        
        successful = [r for r in results if r['success']]
        failed = len(results) - len(successful)
        
        print(f"\n{'='*60}")
        print(f"PERFORMANCE TEST RESULTS")
        print(f"{'='*60}")
        print(f"Total clients: {num_clients}")
        print(f"Successful: {len(successful)}")
        print(f"Failed: {failed}")
        print(f"Success rate: {(len(successful)/num_clients)*100:.2f}%")
        print(f"Total test duration: {total_time:.2f}s")
        
        if successful:
            # Connection times
            conn_times = [r['connection_time'] for r in successful]
            print(f"\n--- Connection Performance ---")
            print(f"Average connection time: {statistics.mean(conn_times):.4f}s")
            print(f"Min: {min(conn_times):.4f}s | Max: {max(conn_times):.4f}s")
            
            # Authentication times
            auth_times = [r['auth_time'] for r in successful]
            print(f"\n--- Authentication Performance ---")
            print(f"Average auth time: {statistics.mean(auth_times):.4f}s")
            print(f"Min: {min(auth_times):.4f}s | Max: {max(auth_times):.4f}s")
            
            # Command execution times
            all_cmd_times = []
            for r in successful:
                all_cmd_times.extend(r['command_times'])
            
            if all_cmd_times:
                print(f"\n--- Command Execution Performance ---")
                print(f"Total commands executed: {len(all_cmd_times)}")
                print(f"Average command time: {statistics.mean(all_cmd_times):.4f}s")
                print(f"Min: {min(all_cmd_times):.4f}s | Max: {max(all_cmd_times):.4f}s")
                print(f"Std deviation: {statistics.stdev(all_cmd_times):.4f}s")
                
                # Throughput
                throughput = len(all_cmd_times) / total_time
                print(f"\nThroughput: {throughput:.2f} commands/second")
            
            # Overall performance
            total_times = [r['total_time'] for r in successful]
            print(f"\n--- Overall Client Performance ---")
            print(f"Average total time per client: {statistics.mean(total_times):.4f}s")
            print(f"Min: {min(total_times):.4f}s | Max: {max(total_times):.4f}s")
        
        print(f"\n{'='*60}\n")

def main():
    print("="*60)
    print("  Secure Remote Execution - Performance Testing")
    print("="*60)
    
    tester = PerformanceTest()
    
    # Test different scenarios
    test_scenarios = [
        (1, 20),    # 1 client, 20 commands
        (5, 10),    # 5 clients, 10 commands each
        (10, 10),   # 10 clients, 10 commands each
        (20, 5),    # 20 clients, 5 commands each
        (50, 5),    # 50 clients, 5 commands each
    ]
    
    all_results = {}
    
    for num_clients, commands_per_client in test_scenarios:
        results = tester.concurrent_clients_test(num_clients, commands_per_client)
        all_results[f"{num_clients}_clients"] = results
        time.sleep(2)  # Cool down between tests
    
    print("\n" + "="*60)
    print("  ALL TESTS COMPLETED")
    print("="*60)

if __name__ == "__main__":
    main()
