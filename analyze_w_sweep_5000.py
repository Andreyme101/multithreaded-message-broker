import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

print("SCRIPT STARTED")

PROJECT_ROOT = Path(r"C:\Users\andre\source\repos\diplom")

INPUT_CSV = PROJECT_ROOT / "all_results_w_sweep_5000.csv"
OUTPUT_AGG = PROJECT_ROOT / "w_sweep_5000_aggregated.csv"
PLOTS_DIR = PROJECT_ROOT / "plots_w_sweep_5000"

print("INPUT_CSV =", INPUT_CSV)
print("EXISTS =", INPUT_CSV.exists())

if not INPUT_CSV.exists():
    raise FileNotFoundError(f"CSV file not found: {INPUT_CSV}")

PLOTS_DIR.mkdir(exist_ok=True)

df = pd.read_csv(INPUT_CSV)

print("Исходных строк:", len(df))
print(df.head())

# Убираем стартовые секунды
df_clean = df[df["sec"] > 2].copy()

print("После удаления стартовых секунд:", len(df_clean))

# Агрегация по каждому прогону
per_run = (
    df_clean
    .groupby(
        ["exp_id", "rate_hint", "W", "Q", "mode", "batch", "batch_wait_us", "work"],
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
)

print("\nАгрегация по прогонам:")
print(per_run)

# Агрегация по W внутри каждого rate
per_w = (
    per_run
    .groupby(
        ["rate_hint", "W", "Q", "mode", "batch", "batch_wait_us", "work"],
        as_index=False
    )
    .agg({
        "received": "median",
        "processed": "median",
        "drops": "median",
        "queue": "median",
        "max_queue": "median",
        "tps": "median",
        "mean_latency_ms": "median",
        "p50_ms": "median",
        "p95_ms": "median",
        "p99_ms": "median",
        "mean_service_ms": "median",
        "mu_per_sec": "median",
        "rho_eff": "median",
        "drop_rate": "median"
    })
    .sort_values(["rate_hint", "W"])
)

print("\nИтог по W:")
print(per_w)

per_w.to_csv(OUTPUT_AGG, index=False, encoding="utf-8-sig")
print("Сохранено:", OUTPUT_AGG)

# Строим графики отдельно для каждого rate
rates = sorted(per_w["rate_hint"].unique())

for rate in rates:
    sub = per_w[per_w["rate_hint"] == rate].sort_values("W")

    # p99 vs W
    plt.figure(figsize=(8, 5))
    plt.plot(sub["W"], sub["p99_ms"], marker="o")
    plt.xlabel("W (workers)")
    plt.ylabel("p99 latency (ms)")
    plt.title(f"p99 vs W (Q=5000, rate={rate})")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / f"plot_p99_vs_w_q5000_rate_{rate}.png", dpi=150)
    plt.close()

    # throughput vs W
    plt.figure(figsize=(8, 5))
    plt.plot(sub["W"], sub["tps"], marker="o")
    plt.xlabel("W (workers)")
    plt.ylabel("throughput / tps")
    plt.title(f"throughput vs W (Q=5000, rate={rate})")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / f"plot_tps_vs_w_q5000_rate_{rate}.png", dpi=150)
    plt.close()

    # p95 vs W
    plt.figure(figsize=(8, 5))
    plt.plot(sub["W"], sub["p95_ms"], marker="o")
    plt.xlabel("W (workers)")
    plt.ylabel("p95 latency (ms)")
    plt.title(f"p95 vs W (Q=5000, rate={rate})")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / f"plot_p95_vs_w_q5000_rate_{rate}.png", dpi=150)
    plt.close()

    # mean latency vs W
    plt.figure(figsize=(8, 5))
    plt.plot(sub["W"], sub["mean_latency_ms"], marker="o")
    plt.xlabel("W (workers)")
    plt.ylabel("mean latency (ms)")
    plt.title(f"mean latency vs W (Q=5000, rate={rate})")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / f"plot_mean_latency_vs_w_q5000_rate_{rate}.png", dpi=150)
    plt.close()

    # queue vs W
    plt.figure(figsize=(8, 5))
    plt.plot(sub["W"], sub["queue"], marker="o")
    plt.xlabel("W (workers)")
    plt.ylabel("mean queue")
    plt.title(f"mean queue vs W (Q=5000, rate={rate})")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / f"plot_queue_vs_w_q5000_rate_{rate}.png", dpi=150)
    plt.close()

    # drop rate vs W
    plt.figure(figsize=(8, 5))
    plt.plot(sub["W"], sub["drop_rate"], marker="o")
    plt.xlabel("W (workers)")
    plt.ylabel("drop rate")
    plt.title(f"drop rate vs W (Q=5000, rate={rate})")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / f"plot_drop_rate_vs_w_q5000_rate_{rate}.png", dpi=150)
    plt.close()

print("Готово.")
print("Графики лежат в папке:", PLOTS_DIR)