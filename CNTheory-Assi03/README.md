# Reliable Data Transfer (RDT) Simulator

This project implements and simulates three Reliable Data Transfer protocols:
1.  **rdt 3.0** (Stop-and-Wait)
2.  **Go-Back-N** (GBN)
3.  **Selective Repeat** (SR)

The simulation uses a beautiful Terminal UI powered by the `rich` library to visualize the sender, receiver, and network state in real-time.

## Features
-   **Unreliable Network Simulation**: Randomly introduces packet loss, corruption, and delays.
-   **Finite State Machines (FSM)**: Each protocol is modeled with its respective sender and receiver logic.
-   **Configurable Parameters**: Set loss and corruption probabilities at startup.
-   **Live Visualization**: Watch packets being sent, acknowledged, or timed out.

## Files
-   `simulator.py`: The main entry point and UI driver.
-   `rdt_protocols.py`: Implementation of RDT 3.0, GBN, and SR.
-   `network.py`: Simulation of the unreliable channel.
-   `packet.py`: Packet structure and checksum logic.

## How to Run
1.  Ensure you have Python installed.
2.  Install the `rich` library if not already present:
    ```bash
    pip install rich
    ```
3.  Run the simulator:
    ```bash
    python simulator.py
    ```
4.  Follow the on-screen prompts to choose a protocol and set network conditions.

## Demo Instructions
When you run the script, you'll be asked to:
-   Select a protocol (1, 2, or 3).
-   Provide loss probability (e.g., 0.1 for 10% loss).
-   Provide corruption probability (e.g., 0.1 for 10% corruption).

The simulation will then start and show a live dashboard of the data transfer.
