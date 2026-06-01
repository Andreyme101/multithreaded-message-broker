import pandas as pd
from pathlib import Path

PROJECT_ROOT = Path(r"C:\Users\andre\source\repos\diplom")
RUN_DIR = PROJECT_ROOT / "results" / "q_sweep_block_w4_work5000"

INPUT_PER_RUN = RUN_DIR / "q_sweep_block_w4_work5000_per_run.csv"
OUTPUT_FINAL = RUN_DIR / "q_sweep_block_w4_work5000_final_summary.csv"

df = pd.read_csv(INPUT_PER_RUN)

GROUP_COLS = ["rate_hint", "Q", "W", "mode", "batch", "batch_wait_us", "work"]

final_summary = (
    df.groupby(GROUP_COLS, as_index=False)
      .agg(
          runs=("exp_id", "count"),

          tps_median=("tps", "median"),
          tps_std=("tps", "std"),
          tps_min=("tps", "min"),
          tps_max=("tps", "max"),

          p99_median=("p99_ms", "median"),
          p99_std=("p99_ms", "std"),
          p99_min=("p99_ms", "min"),
          p99_max=("p99_ms", "max"),

          mean_latency_median=("mean_latency_ms", "median"),
          mean_latency_std=("mean_latency_ms", "std"),
          mean_latency_min=("mean_latency_ms", "min"),
          mean_latency_max=("mean_latency_ms", "max"),

          drop_rate_median=("drop_rate", "median"),
          drop_rate_std=("drop_rate", "std"),
          drop_rate_min=("drop_rate", "min"),
          drop_rate_max=("drop_rate", "max"),
      )
      .sort_values(["rate_hint", "Q"])
)

final_summary.to_csv(OUTPUT_FINAL, index=False, encoding="utf-8-sig")
print("Saved:", OUTPUT_FINAL)
print(final_summary)