"""Run the full Stage 2 campaign with reduced scale for speed."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from captain.experiments.campaign import CampaignRunner, CampaignConfig

config = CampaignConfig(
    seeds=[42, 123, 456, 789, 1024],
    instances_per_family=5,
    families=[
        "BF-A", "BF-B", "BF-C", "BF-D", "BF-E", "BF-F",
        "BF-G", "BF-H", "BF-I", "BF-J", "BF-K",
    ],
    methods=["B1", "B2", "B3", "B4", "B5", "A1", "A2", "A3", "A4", "A5"],
    replay_counts=[1, 3, 5, 10, 20, 50],
    pathway_counts=[1, 2, 3, 5, 10],
    output_dir="research/raw",
)

runner = CampaignRunner(config=config)
result = runner.run_full()
print(f"\nCampaign ID: {result.campaign_id}")
print(f"Seeds completed: {len(result.seed_results)}")
print(f"Granularity instances: {len(result.granularity_results)}")
print(f"Negative controls: {len(result.negative_control_results)}")
