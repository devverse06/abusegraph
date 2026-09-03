from dataclasses import dataclass

@dataclass
class Config:
    seed: int = 42
    customers: int = 10_000
    resource_clusters: int = 700
    min_cluster_size: int = 2
    max_cluster_size: int = 6
    transactions: int = 80_000
    abuse_ring_count: int = 0  # auto-sized from abuse_account_rate_target
    mixed_ring_count: int = 0  # auto-sized from mixed_account_rate_target
    coordination_window_minutes: int = 60
    abuse_account_rate_target: float = 0.05
    mixed_account_rate_target: float = 0.01
    output_dir: str = "output"
    train_fraction: float = 0.70
    validation_fraction: float = 0.15
