from packet import Packet
import time

class RDT30:
    def __init__(self, channel):
        self.channel = channel
        self.seq_num = 0
        self.sender_queue = []
        self.receiver_queue = []
        self.sender_log = []
        self.receiver_log = []
        self.delivered = []
        self.current_msg_idx = 0
        self.waiting_for_ack = False
        self.timer_start = None
        self.timeout = 1.0

    def step(self, messages):
        if self.current_msg_idx >= len(messages) and not self.waiting_for_ack:
            return True # Done

        # Sender Logic
        if not self.waiting_for_ack and self.current_msg_idx < len(messages):
            msg = messages[self.current_msg_idx]
            pkt = Packet(self.seq_num, msg)
            self.sender_log.append(f"[blue]Sender[/]: Sending packet {self.seq_num} ('{msg}')")
            self.channel.send(pkt, self.receiver_queue)
            self.waiting_for_ack = True
            self.timer_start = time.time()

        # Check for Timeout
        if self.waiting_for_ack and (time.time() - self.timer_start > self.timeout):
            self.sender_log.append(f"[red]Sender[/]: Timeout! Retransmitting {self.seq_num}")
            msg = messages[self.current_msg_idx]
            pkt = Packet(self.seq_num, msg)
            self.channel.send(pkt, self.receiver_queue)
            self.timer_start = time.time()

        # Receiver Logic
        if self.receiver_queue:
            pkt = self.receiver_queue.pop(0)
            if pkt.is_corrupt():
                self.receiver_log.append(f"[red]Receiver[/]: Corrupt packet received. Ignoring.")
            elif pkt.seq_num != self.seq_num:
                self.receiver_log.append(f"[yellow]Receiver[/]: Duplicate seq {pkt.seq_num}. Acking previous.")
                ack = Packet(pkt.seq_num, "ACK", is_ack=True)
                self.channel.send(ack, self.sender_queue)
            else:
                self.receiver_log.append(f"[green]Receiver[/]: Received seq {pkt.seq_num} ('{pkt.data}')")
                self.delivered.append(pkt.data)
                ack = Packet(self.seq_num, "ACK", is_ack=True)
                self.channel.send(ack, self.sender_queue)

        # Handle ACKs
        if self.sender_queue:
            ack_pkt = self.sender_queue.pop(0)
            if not ack_pkt.is_corrupt() and ack_pkt.ack_num == self.seq_num:
                self.sender_log.append(f"[green]Sender[/]: Received ACK {self.seq_num}")
                self.waiting_for_ack = False
                self.seq_num = 1 - self.seq_num
                self.current_msg_idx += 1
            else:
                self.sender_log.append(f"[yellow]Sender[/]: Corrupt or wrong ACK {ack_pkt.ack_num}")

        return False

class GBN:
    def __init__(self, channel, window_size=4):
        self.channel = channel
        self.window_size = window_size
        self.base = 0
        self.next_seq_num = 0
        self.expected_seq_num = 0
        self.sender_queue = []
        self.receiver_queue = []
        self.sender_log = []
        self.receiver_log = []
        self.delivered = []
        self.timer_start = None
        self.timeout = 1.5
        self.packets = []

    def step(self, messages):
        if not self.packets:
            self.packets = [Packet(i, m) for i, m in enumerate(messages)]

        if self.base >= len(messages):
            return True

        # Sender: Fill window
        while self.next_seq_num < self.base + self.window_size and self.next_seq_num < len(messages):
            pkt = self.packets[self.next_seq_num]
            self.sender_log.append(f"[blue]Sender[/]: Sending packet {pkt.seq_num}")
            self.channel.send(pkt, self.receiver_queue)
            if self.base == self.next_seq_num:
                self.timer_start = time.time()
            self.next_seq_num += 1

        # Timeout handling
        if self.timer_start and (time.time() - self.timer_start > self.timeout):
            self.sender_log.append(f"[red]Sender[/]: Timeout! Retransmitting window from {self.base}")
            self.timer_start = time.time()
            for i in range(self.base, self.next_seq_num):
                self.channel.send(self.packets[i], self.receiver_queue)

        # Receiver
        if self.receiver_queue:
            pkt = self.receiver_queue.pop(0)
            if not pkt.is_corrupt() and pkt.seq_num == self.expected_seq_num:
                self.receiver_log.append(f"[green]Receiver[/]: Received in-order {pkt.seq_num}")
                self.delivered.append(pkt.data)
                ack = Packet(self.expected_seq_num, "ACK", is_ack=True)
                self.channel.send(ack, self.sender_queue)
                self.expected_seq_num += 1
            else:
                reason = "corrupt" if pkt.is_corrupt() else f"out-of-order (expected {self.expected_seq_num}, got {pkt.seq_num})"
                self.receiver_log.append(f"[yellow]Receiver[/]: {reason}. Resending ACK {self.expected_seq_num - 1}")
                ack = Packet(self.expected_seq_num - 1, "ACK", is_ack=True)
                self.channel.send(ack, self.sender_queue)

        # ACKs
        if self.sender_queue:
            ack_pkt = self.sender_queue.pop(0)
            if not ack_pkt.is_corrupt():
                self.sender_log.append(f"[green]Sender[/]: Received ACK {ack_pkt.ack_num}")
                self.base = ack_pkt.ack_num + 1
                if self.base == self.next_seq_num:
                    self.timer_start = None
                else:
                    self.timer_start = time.time()
        
        return False

class SR:
    def __init__(self, channel, window_size=4):
        self.channel = channel
        self.window_size = window_size
        self.base = 0
        self.next_seq_num = 0
        self.sender_queue = []
        self.receiver_queue = []
        self.sender_log = []
        self.receiver_log = []
        self.delivered = []
        self.delivered_pkts = {} # Buffer for out-of-order
        self.expected_delivery_seq = 0
        self.ack_status = {} # {seq: (is_acked, send_time)}
        self.timeout = 2.0
        self.packets = []

    def step(self, messages):
        if not self.packets:
            self.packets = [Packet(i, m) for i, m in enumerate(messages)]
            for i in range(len(messages)):
                self.ack_status[i] = [False, 0]

        if self.base >= len(messages):
            return True

        # Sender: Fill window
        while self.next_seq_num < self.base + self.window_size and self.next_seq_num < len(messages):
            pkt = self.packets[self.next_seq_num]
            self.sender_log.append(f"[blue]Sender[/]: Sending packet {pkt.seq_num}")
            self.channel.send(pkt, self.receiver_queue)
            self.ack_status[self.next_seq_num][1] = time.time()
            self.next_seq_num += 1

        # Check individual timeouts
        for i in range(self.base, self.next_seq_num):
            if not self.ack_status[i][0] and (time.time() - self.ack_status[i][1] > self.timeout):
                self.sender_log.append(f"[red]Sender[/]: Timeout for packet {i}! Retransmitting.")
                self.channel.send(self.packets[i], self.receiver_queue)
                self.ack_status[i][1] = time.time()

        # Receiver
        if self.receiver_queue:
            pkt = self.receiver_queue.pop(0)
            if not pkt.is_corrupt():
                self.receiver_log.append(f"[green]Receiver[/]: Received packet {pkt.seq_num}")
                self.delivered_pkts[pkt.seq_num] = pkt.data
                
                # Check if we can deliver in-order packets
                while self.expected_delivery_seq in self.delivered_pkts:
                    self.delivered.append(self.delivered_pkts[self.expected_delivery_seq])
                    self.expected_delivery_seq += 1

                ack = Packet(pkt.seq_num, "ACK", is_ack=True)
                self.channel.send(ack, self.sender_queue)
            else:
                self.receiver_log.append(f"[red]Receiver[/]: Corrupt packet received.")

        # ACKs
        if self.sender_queue:
            ack_pkt = self.sender_queue.pop(0)
            if not ack_pkt.is_corrupt():
                self.sender_log.append(f"[green]Sender[/]: Received ACK {ack_pkt.ack_num}")
                if ack_pkt.ack_num in self.ack_status:
                    self.ack_status[ack_pkt.ack_num][0] = True
                
                # Advance window
                while self.base < len(messages) and self.ack_status[self.base][0]:
                    self.base += 1

        return False

