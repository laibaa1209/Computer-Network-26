import time
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.live import Live
from rich.table import Table
from rich.columns import Columns
from rich import box

from network import NetworkChannel
from rdt_protocols import RDT30, GBN, SR

console = Console()

def make_layout():
    layout = Layout()
    layout.split(
        Layout(name="header", size=3),
        Layout(name="main", ratio=1),
        Layout(name="footer", size=3),
    )
    layout["main"].split_row(
        Layout(name="sender"),
        Layout(name="network", ratio=2),
        Layout(name="receiver"),
    )
    return layout

class Header:
    def __init__(self, protocol_name):
        self.protocol_name = protocol_name

    def __rich__(self):
        grid = Table.grid(expand=True)
        grid.add_column(justify="center", ratio=1)
        grid.add_row(f"[bold magenta]Reliable Data Transfer Simulator - {self.protocol_name}[/bold magenta]")
        return Panel(grid, style="white on blue")

def run_simulation(protocol_type, messages, loss=0.1, corrupt=0.1):
    channel = NetworkChannel(loss_prob=loss, corruption_prob=corrupt)
    
    if protocol_type == "RDT3.0":
        proto = RDT30(channel)
    elif protocol_type == "GBN":
        proto = GBN(channel, window_size=4)
    elif protocol_type == "SR":
        proto = SR(channel, window_size=4)
    
    layout = make_layout()
    layout["header"].update(Header(protocol_type))
    
    with Live(layout, refresh_per_second=4, screen=True):
        while True:
            done = proto.step(messages)
            
            # Update Sender Panel
            sender_log = "\n".join(proto.sender_log[-10:])
            layout["sender"].update(Panel(sender_log, title="Sender Log", border_style="blue"))
            
            # Update Receiver Panel
            receiver_log = "\n".join(proto.receiver_log[-10:])
            layout["receiver"].update(Panel(receiver_log, title="Receiver Log", border_style="green"))
            
            # Update Network/Status Panel
            status_table = Table(box=box.SIMPLE)
            status_table.add_column("Property")
            status_table.add_column("Value")
            status_table.add_row("Messages Sent", f"{getattr(proto, 'current_msg_idx', getattr(proto, 'next_seq_num', 0))}/{len(messages)}")
            status_table.add_row("Messages Delivered", f"{len(getattr(proto, 'delivered', getattr(proto, 'delivered_pkts', {})))}/{len(messages)}")
            
            if hasattr(proto, 'base'):
                status_table.add_row("Window Base", str(proto.base))
                status_table.add_row("Next Seq", str(proto.next_seq_num))
            
            layout["network"].update(Panel(status_table, title="Simulation Status", border_style="magenta"))
            
            if done:
                layout["footer"].update(Panel("[bold green]Simulation Complete! Press Ctrl+C to exit.[/bold green]", border_style="white"))
                time.sleep(2)
                break
            
            time.sleep(0.2)

if __name__ == "__main__":
    import sys
    msgs = ["Hello", "World", "Reliable", "Data", "Transfer", "Test", "Final"]
    
    console.print("[bold cyan]Choose Protocol:[/bold cyan]")
    console.print("1. RDT 3.0 (Stop-and-Wait)")
    console.print("2. Go-Back-N (GBN)")
    console.print("3. Selective Repeat (SR)")
    
    choice = input("Enter choice (1-3): ")
    
    proto_map = {"1": "RDT3.0", "2": "GBN", "3": "SR"}
    protocol = proto_map.get(choice, "RDT3.0")
    
    loss = float(input("Enter packet loss probability (0.0-1.0) [0.1]: ") or 0.1)
    corrupt = float(input("Enter packet corruption probability (0.0-1.0) [0.1]: ") or 0.1)
    
    run_simulation(protocol, msgs, loss, corrupt)
