class CongestionControl:
    def __init__(self, MSS: int):
        self.current_state = "slow start"
        self.MSS = MSS
        self.cwnd = 1 * self.MSS
        self.ssthresh = None

    def get_cwnd(self)-> bytes:
        return self.cwnd

    def get_MSS_in_cwnd(self)-> int:
        return self.cwnd // self.MSS

    def event_ack_received(self):
        if self.current_state == "slow start":
            self.cwnd += self.MSS
            if self.ssthresh is not None and self.cwnd >= self.ssthresh:
                self.current_state = "congestion avoidance"
        elif self.current_state == "congestion avoidance":
            aumento = self.MSS / self.get_MSS_in_cwnd()
            self.cwnd += aumento
            
    def event_timeout(self):
        self.ssthresh = max(self.cwnd // 2, 1 * self.MSS)
        self.cwnd = 1 * self.MSS
        self.current_state = "slow start"
        
    def is_state_slow_start(self) -> bool:
        return self.current_state == "slow start"

    def is_state_congestion_avoidance(self) -> bool:
        return self.current_state == "congestion avoidance"

    def get_ssthresh(self):
        return self.ssthresh