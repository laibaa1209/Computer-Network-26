# Technical Report: DNS System Simulation
**Project Name:** Distributed Hierarchical DNS Simulation  
**Assignment:** Computer Networks - Assignment II  
**Student:** Preparatory Materials for Viva  

---

## 1. Project Overview
The objective of this project was to simulate a real-world **DNS (Domain Name System)** hierarchy using Python. The system demonstrates how a domain name (like `google.com`) is translated into an IP address through a series of distributed server interactions.

### 2. Core Architecture
The simulation follows the official DNS hierarchy:
1.  **Resolver (Recursive)**: The entry point for the user. It manages the entire search process and caches results.
2.  **Root Server (`.` )**: The top of the hierarchy. It knows which TLD servers handle specific extensions (like `.com`).
3.  **TLD Server (`.com` )**: Handles Top-Level Domain info. It refers the resolver to the specific Authoritative server for a domain.
4.  **Authoritative Server**: The final source of truth that contains the actual DNS records (IPs, MX records, etc.).

---

## 3. Latest Implementation Changes
I have significantly upgraded the system from a basic simulation to a professional-grade protocol demonstration.

### A. Recursive Resolver Logic
*   **Previous**: The client had to talk to each server one by one (Iterative).
*   **Update**: Implemented a **Recursive Resolver**. The client now sends one query, and the resolver does the "legwork," contacting every server in the chain until it finds the answer.
*   **Caching**: Added an in-memory cache to the resolver. Identical subsequent queries are answered instantly without contacting outer servers, simulating real-world ISP DNS behavior.

### B. Professional Referrals (NS & SRV)
*   **Previous**: Used simple "TXTHacks" to pass port numbers between servers.
*   **Update**: Implemented **Standard Referrals**. 
    *   Servers now return **NS (Name Server)** records in the *Authority* section.
    *   They return **SRV (Service)** records in the *Additional* section (acting as "Glue records") to provide the specific port of the next server. This is the correct protocol-oriented way to handle non-standard ports.

### C. Advanced Record Support
*   **CNAME Support**: Added support for Canonical names (aliasing). If a domain points to another, the system follows the chain.
*   **MX & TXT**: Added support for Mail Exchange (MX) and Text (TXT) records, allowing the system to simulate email server lookups and SPF/Security records.
*   **Type Safety**: Re-engineered the packet handling to manually handle `QTYPE` integers, bypassing library-specific limitations in `dnslib`.

### D. Visual Interface
*   **Color-Coded CLI**: Integrated `colorama` to provide a clear, color-coded walkthrough of the resolution process.
    *   `MAGENTA`: Root Server
    *   `YELLOW`: TLD Server
    *   `CYAN`: Authoritative Server
    *   `GREEN`: Recursive Resolver

---

## 4. Resolution Walkthrough (For Viva)
When you query `google.com`:
1.  **LocalHost** sends a query to the **Recursive Resolver** (Port 8000).
2.  **Resolver** checks its **Cache**. (Miss).
3.  **Resolver** contacts **Root Server** (Port 8001). Root responds with an **NS record** for `.com` and an **SRV record** for the TLD port (8002).
4.  **Resolver** contacts **TLD Server** (Port 8002). TLD responds with an **NS record** for `google.com` and an **SRV record** for the Auth port (8003).
5.  **Resolver** contacts **Authoritative Server** (Port 8003). Auth returns the **A record** (IP).
6.  **Resolver** stores the IP in **Cache** and returns it to **LocalHost**.

---

## 5. Technical Stack
*   **Language**: Python 3
*   **Library**: `dnslib` (for binary packet parsing/construction)
*   **Logic**: Socket Programming (UDP/DGRAM)
*   **UI**: Colorama
