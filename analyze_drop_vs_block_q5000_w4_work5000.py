import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

print("SCRIPT STARTED")

PROJECT_ROOT = Path(r"C:\Users\andre\source\repos\diplom")
RUN_DIR = PROJECT_ROOT / "results" / "drop_vs_block_q5000_w4_work5000"

INPUT_CSV = RUN_DIR / "all_results_drop_vs_block_q5000_w4_work5000.csv"
OUTPUT_AGG = RUN_DIR / "drop_vs_block_q5000_w4_work5000_aggregated.csv"
OUTPUT_PER_RUN = RUN_DIR / "drop_vs_block_q5000_w4_work5000_per_run.csv"
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
        ["exp_id", "mode", "rate_hint", "W", "Q", "batch", "batch_wait_us", "work"],
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
    .sort_values(["mode", "rate_hint", "exp_id"])
)

print("\nАгрегация по прогонам:")
print(per_run)

per_run.to_csv(OUTPUT_PER_RUN, index=False, encoding="utf-8-sig")
print("Сохранено per_run:", OUTPUT_PER_RUN)

# Итог по mode + rate
per_cfg = (
    per_run
    .groupby(
        ["mode", "rate_hint", "W", "Q", "batch", "batch_wait_us", "work"],
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
    .sort_values(["mode", "rate_hint"])
)

print("\nИтог по mode + rate:")
print(per_cfg)

per_cfg.to_csv(OUTPUT_AGG, index=False, encoding="utf-8-sig")
print("Сохранено:", OUTPUT_AGG)

# ---------------------------
# Графики: сравнение drop vs block
# ---------------------------

modes = sorted(per_cfg["mode"].unique())
rates = sorted(per_cfg["rate_hint"].unique())

def plot_metric(metric_col, ylabel, title, filename):
    plt.figure(figsize=(8, 5))
    for mode in modes:
        sub = per_cfg[per_cfg["mode"] == mode].sort_values("rate_hint")
        plt.plot(sub["rate_hint"], sub[metric_col], marker="o", label=mode)
    plt.xlabel("input rate")
    plt.ylabel(ylabel)
    plt.title(title)
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / filename, dpi=150)
    plt.close()

plot_metric("tps_median",
            "throughput / tps (median)",
            "throughput vs input rate (drop vs block)",
            "plot_tps_vs_rate_drop_vs_block.png")

plot_metric("mean_latency_median",
            "mean latency (ms, median)",
            "mean latency vs input rate (drop vs block)",
            "plot_mean_latency_vs_rate_drop_vs_block.png")

plot_metric("p95_median",
            "p95 latency (ms, median)",
            "p95 vs input rate (drop vs block)",
            "plot_p95_vs_rate_drop_vs_block.png")

plot_metric("p99_median",
            "p99 latency (ms, median)",
            "p99 vs input rate (drop vs block)",
            "plot_p99_vs_rate_drop_vs_block.png")

plot_metric("queue_median",
            "mean queue (median)",
            "mean queue vs input rate (drop vs block)",
            "plot_queue_vs_rate_drop_vs_block.png")

plot_metric("max_queue_median",
            "max queue (median)",
            "max queue vs input rate (drop vs block)",
            "plot_max_queue_vs_rate_drop_vs_block.png")

plot_metric("drop_rate_median",
            "drop rate (median)",
            "drop rate vs input rate (drop vs block)",
            "plot_drop_rate_vs_rate_drop_vs_block.png")

plot_metric("rho_eff_median",
            "rho_eff (median)",
            "rho_eff vs input rate (drop vs block)",
            "plot_rho_eff_vs_rate_drop_vs_block.png")

# ---------------------------
# Boxplot throughput по mode/rate
# ---------------------------

labels = []
data_tps = []

for mode in modes:
    for rate in rates:
        vals = per_run[(per_run["mode"] == mode) & (per_run["rate_hint"] == rate)]["tps"].values
        labels.append(f"{mode}\n{rate}")
        data_tps.append(vals)

plt.figure(figsize=(10, 5))
plt.boxplot(data_tps, tick_labels=labels)
plt.xlabel("mode / input rate")
plt.ylabel("throughput / tps per run")
plt.title("throughput distribution (drop vs block)")
plt.grid(True)
plt.tight_layout()
plt.savefig(PLOTS_DIR / "plot_tps_boxplot_drop_vs_block.png", dpi=150)
plt.close()

# ---------------------------
# Boxplot p99 по mode/rate
# ---------------------------

labels = []
data_p99 = []

for mode in modes:
    for rate in rates:
        vals = per_run[(per_run["mode"] == mode) & (per_run["rate_hint"] == rate)]["p99_ms"].values
        labels.append(f"{mode}\n{rate}")
        data_p99.append(vals)

plt.figure(figsize=(10, 5))
plt.boxplot(data_p99, tick_labels=labels)
plt.xlabel("mode / input rate")
plt.ylabel("p99 latency per run (ms)")
plt.title("p99 distribution (drop vs block)")
plt.grid(True)
plt.tight_layout()
plt.savefig(PLOTS_DIR / "plot_p99_boxplot_drop_vs_block.png", dpi=150)
plt.close()

print("Готово.")
print("Графики лежат в:", PLOTS_DIR)