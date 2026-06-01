import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

print("SCRIPT STARTED")

PROJECT_ROOT = Path(r"C:\Users\andre\source\repos\diplom")
RUN_DIR = PROJECT_ROOT / "results" / "q_sweep_block_w4_work5000"

INPUT_CSV = RUN_DIR / "all_results_q_sweep_block_w4_work5000.csv"
OUTPUT_AGG = RUN_DIR / "q_sweep_block_w4_work5000_aggregated.csv"
OUTPUT_PER_RUN = RUN_DIR / "q_sweep_block_w4_work5000_per_run.csv"
PLOTS_DIR = RUN_DIR / "plots"

print("INPUT_CSV =", INPUT_CSV)
print("EXISTS =", INPUT_CSV.exists())

if not INPUT_CSV.exists():
    raise FileNotFoundError(f"CSV file not found: {INPUT_CSV}")

PLOTS_DIR.mkdir(exist_ok=True)

df = pd.read_csv(INPUT_CSV)

print("Исходных строк:", len(df))
print(df.head())

# Убираем warmup
df_clean = df[df["sec"] > 3].copy()

print("После удаления стартовых секунд:", len(df_clean))

# Агрегация по каждому прогону
per_run = (
    df_clean
    .groupby(
        ["exp_id", "rate_hint", "Q", "W", "mode", "batch", "batch_wait_us", "work"],
        as_index=False
    )
    .agg({
        "received": "max",
        "processed": "max",
        "drops": "max",
        "queue": "mean",
        "max_queue": "max",
        "tps": "mean",
        "mean_latency_ms": "mean",
        "p50_ms": "mean",
        "p95_ms": "mean",
        "p99_ms": "mean",
        "mean_service_ms": "mean",
        "mu_per_sec": "mean",
        "rho_eff": "mean",
        "drop_rate": "mean"
    })
    .sort_values(["rate_hint", "Q", "exp_id"])
)

print("\nАгрегация по прогонам:")
print(per_run)

per_run.to_csv(OUTPUT_PER_RUN, index=False, encoding="utf-8-sig")
print("Сохранено per_run:", OUTPUT_PER_RUN)

# Итог по Q внутри каждого rate
per_cfg = (
    per_run
    .groupby(
        ["rate_hint", "Q", "W", "mode", "batch", "batch_wait_us", "work"],
        as_index=False
    )
    .agg(
        received_median=("received", "median"),
        processed_median=("processed", "median"),
        drops_median=("drops", "median"),
        queue_median=("queue", "median"),
        max_queue_median=("max_queue", "median"),
        tps_median=("tps", "median"),
        tps_mean=("tps", "mean"),
        tps_std=("tps", "std"),
        mean_latency_median=("mean_latency_ms", "median"),
        mean_latency_mean=("mean_latency_ms", "mean"),
        mean_latency_std=("mean_latency_ms", "std"),
        p95_median=("p95_ms", "median"),
        p95_mean=("p95_ms", "mean"),
        p95_std=("p95_ms", "std"),
        p99_median=("p99_ms", "median"),
        p99_mean=("p99_ms", "mean"),
        p99_std=("p99_ms", "std"),
        queue_mean=("queue", "mean"),
        queue_std=("queue", "std"),
        max_queue_mean=("max_queue", "mean"),
        max_queue_std=("max_queue", "std"),
        drop_rate_median=("drop_rate", "median"),
        drop_rate_mean=("drop_rate", "mean"),
        drop_rate_std=("drop_rate", "std"),
        rho_eff_median=("rho_eff", "median"),
        rho_eff_mean=("rho_eff", "mean"),
        rho_eff_std=("rho_eff", "std"),
    )
    .sort_values(["rate_hint", "Q"])
)

print("\nИтог по Q:")
print(per_cfg)

per_cfg.to_csv(OUTPUT_AGG, index=False, encoding="utf-8-sig")
print("Сохранено:", OUTPUT_AGG)

# ---------------------------
# Графики: отдельно для каждого rate, по оси X = Q
# ---------------------------

rates = sorted(per_cfg["rate_hint"].unique())

for rate in rates:
    sub = per_cfg[per_cfg["rate_hint"] == rate].sort_values("Q")

    # throughput
    plt.figure(figsize=(8, 5))
    plt.plot(sub["Q"], sub["tps_median"], marker="o")
    plt.xlabel("Q (queue size)")
    plt.ylabel("throughput / tps (median)")
    plt.title(f"throughput vs Q (rate={rate}, mode=block)")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / f"plot_tps_vs_q_rate_{rate}.png", dpi=150)
    plt.close()

    # mean latency
    plt.figure(figsize=(8, 5))
    plt.plot(sub["Q"], sub["mean_latency_median"], marker="o")
    plt.xlabel("Q (queue size)")
    plt.ylabel("mean latency (ms, median)")
    plt.title(f"mean latency vs Q (rate={rate}, mode=block)")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / f"plot_mean_latency_vs_q_rate_{rate}.png", dpi=150)
    plt.close()

    # p95
    plt.figure(figsize=(8, 5))
    plt.plot(sub["Q"], sub["p95_median"], marker="o")
    plt.xlabel("Q (queue size)")
    plt.ylabel("p95 latency (ms, median)")
    plt.title(f"p95 vs Q (rate={rate}, mode=block)")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / f"plot_p95_vs_q_rate_{rate}.png", dpi=150)
    plt.close()

    # p99
    plt.figure(figsize=(8, 5))
    plt.plot(sub["Q"], sub["p99_median"], marker="o")
    plt.xlabel("Q (queue size)")
    plt.ylabel("p99 latency (ms, median)")
    plt.title(f"p99 vs Q (rate={rate}, mode=block)")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / f"plot_p99_vs_q_rate_{rate}.png", dpi=150)
    plt.close()

    # mean queue
    plt.figure(figsize=(8, 5))
    plt.plot(sub["Q"], sub["queue_median"], marker="o")
    plt.xlabel("Q (queue size)")
    plt.ylabel("mean queue (median)")
    plt.title(f"mean queue vs Q (rate={rate}, mode=block)")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / f"plot_queue_vs_q_rate_{rate}.png", dpi=150)
    plt.close()

    # max queue
    plt.figure(figsize=(8, 5))
    plt.plot(sub["Q"], sub["max_queue_median"], marker="o")
    plt.xlabel("Q (queue size)")
    plt.ylabel("max queue (median)")
    plt.title(f"max queue vs Q (rate={rate}, mode=block)")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / f"plot_max_queue_vs_q_rate_{rate}.png", dpi=150)
    plt.close()

    # drop rate
    plt.figure(figsize=(8, 5))
    plt.plot(sub["Q"], sub["drop_rate_median"], marker="o")
    plt.xlabel("Q (queue size)")
    plt.ylabel("drop rate (median)")
    plt.title(f"drop rate vs Q (rate={rate}, mode=block)")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / f"plot_drop_rate_vs_q_rate_{rate}.png", dpi=150)
    plt.close()

    # rho_eff
    plt.figure(figsize=(8, 5))
    plt.plot(sub["Q"], sub["rho_eff_median"], marker="o")
    plt.xlabel("Q (queue size)")
    plt.ylabel("rho_eff (median)")
    plt.title(f"rho_eff vs Q (rate={rate}, mode=block)")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / f"plot_rho_eff_vs_q_rate_{rate}.png", dpi=150)
    plt.close()

# ---------------------------
# Boxplot throughput отдельно по rate/Q
# ---------------------------

labels = []
data_tps = []

for rate in rates:
    sub_rate = per_run[per_run["rate_hint"] == rate]
    qs = sorted(sub_rate["Q"].unique())
    for q in qs:
        vals = sub_rate[sub_rate["Q"] == q]["tps"].values
        labels.append(f"{rate}\nQ={q}")
        data_tps.append(vals)

plt.figure(figsize=(10, 5))
plt.boxplot(data_tps, tick_labels=labels)
plt.xlabel("rate / Q")
plt.ylabel("throughput / tps per run")
plt.title("throughput distribution by Q (mode=block)")
plt.grid(True)
plt.tight_layout()
plt.savefig(PLOTS_DIR / "plot_tps_boxplot_q_sweep.png", dpi=150)
plt.close()

# ---------------------------
# Boxplot p99 отдельно по rate/Q
# ---------------------------

labels = []
data_p99 = []

for rate in rates:
    sub_rate = per_run[per_run["rate_hint"] == rate]
    qs = sorted(sub_rate["Q"].unique())
    for q in qs:
        vals = sub_rate[sub_rate["Q"] == q]["p99_ms"].values
        labels.append(f"{rate}\nQ={q}")
        data_p99.append(vals)

plt.figure(figsize=(10, 5))
plt.boxplot(data_p99, tick_labels=labels)
plt.xlabel("rate / Q")
plt.ylabel("p99 latency per run (ms)")
plt.title("p99 distribution by Q (mode=block)")
plt.grid(True)
plt.tight_layout()
plt.savefig(PLOTS_DIR / "plot_p99_boxplot_q_sweep.png", dpi=150)
plt.close()

print("Готово.")
print("Графики лежат в:", PLOTS_DIR)