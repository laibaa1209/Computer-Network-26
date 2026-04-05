import socket
import struct
import threading
import random
import time
from collections import deque

#CONFIGURATION (Ports for our "Network")
RESOLVER_ADDR = ("127.0.0.1", 8000)
ROOT_ADDR = ("127.0.0.1", 8001)
TLD_ADDR = ("127.0.0.1", 8002)
AUTH_ADDR = ("127.0.0.1", 8003)

#DNS PACKET HELPER
# Format: !HH (Two 16-bit unsigned shorts in Network Byte Order)
# Packet structure: [Identification (16-bit)][Flags (16-bit)][Data...]

def create_dns_packet(id_val, flags, data):
    """Encodes a 16-bit ID and 16-bit Flags into a binary packet."""
    header = struct.pack("!HH", id_val, flags)
    return header + data.encode('utf-8')

def parse_dns_packet(packet):
    """Decodes the 16-bit ID and Flags from a binary packet."""
    header_size = struct.calcsize("!HH")
    id_val, flags = struct.unpack("!HH", packet[:header_size])
    data = packet[header_size:].decode('utf-8')
    return id_val, flags, data

#SERVER IMPLEMENTATIONS
class DNSServerBase:
    def __init__(self, name, addr):
        self.name = name
        self.addr = addr
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(self.addr)
        print(f"[*] {self.name} started listening on {self.addr}")

    def run(self):
        while True:
            data, client_addr = self.sock.recvfrom(1024)
            tid, flags, query = parse_dns_packet(data)
            print(f"[#] {self.name} received query: '{query}' (ID: {hex(tid)})")
            
            response_data = self.handle_query(query)
            
            # Set QR flag (Response) in 16-bit flags
            response_flags = flags | 0x8000 
            packet = create_dns_packet(tid, response_flags, response_data)
            self.sock.sendto(packet, client_addr)

    def handle_query(self, query):
        raise NotImplementedError

class AuthoritativeServer(DNSServerBase):
    def __init__(self):
        super().__init__("Authoritative Server", AUTH_ADDR)
        self.records = {
            'google.com': "A:64.233.187.99,72.14.207.99|NS:ns1.google.com|MX:10 smtp1.google.com",
            'microsoft.com': "A:20.112.52.29|NS:ns1-07.azure-dns.com|MX:10 microsoft-com.mail.protection.outlook.com",
            'yahoo.com': "A:98.137.11.163|NS:ns1.yahoo.com|MX:10 mta1.yahoo.com"
        }

    def handle_query(self, query):
        return self.records.get(query, "ERROR:NOT_FOUND")

class TLDServer(DNSServerBase):
    def __init__(self):
        super().__init__("TLD Server (.com)", TLD_ADDR)
        self.referrals = {
            'google.com': f"{AUTH_ADDR[0]}:{AUTH_ADDR[1]}",
            'microsoft.com': f"{AUTH_ADDR[0]}:{AUTH_ADDR[1]}",
            'yahoo.com': f"{AUTH_ADDR[0]}:{AUTH_ADDR[1]}"
        }

    def handle_query(self, query):
        # In actual DNS, it returns the IP of the next server
        return self.referrals.get(query, "ERROR:TLD_UNKNOWN")

class RootServer(DNSServerBase):
    def __init__(self):
        super().__init__("Root Server", ROOT_ADDR)
        self.tlds = {
            'com': f"{TLD_ADDR[0]}:{TLD_ADDR[1]}",
            'org': f"{TLD_ADDR[0]}:{TLD_ADDR[1]}", # Simplified
        }

    def handle_query(self, query):
        tld = query.split('.')[-1]
        return self.tlds.get(tld, "ERROR:ROOT_UNKNOWN")

#LOCAL HOST / RESOLVER (CLIENT)

class LocalHost:
    def __init__(self, cache_limit=3):
        self.cache = {}
        self.cache_order = deque()
        self.cache_limit = cache_limit
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Timeout to prevent hanging if a server is down
        self.sock.settimeout(2.0)

    def flush_cache(self):
        if len(self.cache) >= self.cache_limit:
            oldest = self.cache_order.popleft()
            print(f"  [Cache Management] Auto-flushing oldest record: {oldest}")
            del self.cache[oldest]

    def add_to_cache(self, domain, record):
        if domain not in self.cache:
            self.flush_cache()
            self.cache_order.append(domain)
        self.cache[domain] = record
        print(f"  [Cache Management] Stored in cache: {domain}")

    def query_server(self, addr, query):
        tid = random.getrandbits(16)
        # Flags=0 (Query)
        packet = create_dns_packet(tid, 0, query)
        self.sock.sendto(packet, addr)
        try:
            data, _ = self.sock.recvfrom(1024)
            rid, flags, result = parse_dns_packet(data)
            # Verify ID matches (Basic Security)
            if rid == tid:
                return result
        except socket.timeout:
            return "ERROR:TIMEOUT"

    def resolve(self, domain):
        print(f"\n--- [Local Host] Resolving: {domain} ---")
        
        # 1. Check Cache
        if domain in self.cache:
            print(f"  [Cache] Found cached result!")
            self.display_result(domain, self.cache[domain])
            return

        # 2. Iterate through Servers (Real networking calls)
        print("  [Step 1] Contacting Root Server...")
        tld_meta = self.query_server(ROOT_ADDR, domain)
        
        if "ERROR" not in tld_meta:
            print(f"  [Step 2] Root referred to TLD: {tld_meta}. Contacting TLD...")
            tld_port = int(tld_meta.split(':')[-1])
            auth_meta = self.query_server(("127.0.0.1", tld_port), domain)
            
            if "ERROR" not in auth_meta:
                print(f"  [Step 3] TLD referred to Auth Server: {auth_meta}. Contacting Auth...")
                auth_port = int(auth_meta.split(':')[-1])
                final_record = self.query_server(("127.0.0.1", auth_port), domain)
                
                if "ERROR" not in final_record:
                    self.add_to_cache(domain, final_record)
                    self.display_result(domain, final_record)
                    return

        print(f"  [Error] Failed to resolve {domain}. {tld_meta}")

    def display_result(self, domain, record):
        # Format: A:64.233.187.99|NS:ns1.google.com|MX:10 smtp1.google.com
        parts = record.split('|')
        a_records = parts[0].split(':')[-1]
        print(f"\n{domain}/{a_records.split(',')[0]} (Retrieved via Network)")
        print("-- DNS INFORMATION --")
        for p in parts:
            print(p)

#SYSTEM BOOTSTRAP

def run_servers():
    """Function to start all background servers in threads."""
    root = RootServer()
    tld = TLDServer()
    auth = AuthoritativeServer()
    
    # Run them in separate threads so the main program can act as the client
    threading.Thread(target=root.run, daemon=True).start()
    threading.Thread(target=tld.run, daemon=True).start()
    threading.Thread(target=auth.run, daemon=True).start()

if __name__ == "__main__":
    # 1. Start the actual network servers
    run_servers()
    time.sleep(1) # Give servers a second to bind
    
    # 2. Create the Local PC (The client)
    my_pc = LocalHost(cache_limit=2)

    # 3. Perform network lookups
    my_pc.resolve("google.com")
    
    # 4. Show Caching in Action (No network hops printed this time)
    time.sleep(1)
    my_pc.resolve("google.com")

    # 5. Populate cache and show auto-flushing
    my_pc.resolve("microsoft.com")
    my_pc.resolve("yahoo.com") # Should trigger flush of google.com
