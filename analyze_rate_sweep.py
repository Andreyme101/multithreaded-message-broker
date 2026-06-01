import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

print("SCRIPT STARTED")

PROJECT_ROOT = Path(r"C:\Users\andre\source\repos\diplom")
INPUT_CSV = PROJECT_ROOT / "all_results_rate_sweep.csv"
OUTPUT_AGG = PROJECT_ROOT / "rate_sweep_aggregated.csv"

print("INPUT_CSV =", INPUT_CSV)
print("EXISTS =", INPUT_CSV.exists())

df = pd.read_csv(INPUT_CSV)

print("Исходных строк:", len(df))
print(df.head())

# убираем стартовые секунды
df_clean = df[df["sec"] > 2].copy()

print("После удаления стартовых секунд:", len(df_clean))

# агрегация по одному запуску
per_run = (
    df_clean
    .groupby(["exp_id", "rate_hint", "W", "Q", "mode", "batch", "batch_wait_us", "work"], as_index=False)
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

# агрегация по rate
per_rate = (
    per_run
    .groupby(["rate_hint", "W", "Q", "mode", "batch", "batch_wait_us", "work"], as_index=False)
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
    .sort_values("rate_hint")
)

print("\nИтог по rate:")
print(per_rate)

per_rate.to_csv(OUTPUT_AGG, index=False, encoding="utf-8-sig")
print("Сохранено:", OUTPUT_AGG)

# p99 vs rate
plt.figure(figsize=(8, 5))
plt.plot(per_rate["rate_hint"], per_rate["p99_ms"], marker="o")
plt.xlabel("rate (messages/sec)")
plt.ylabel("p99 latency (ms)")
plt.title("p99 vs rate")
plt.grid(True)
plt.tight_layout()
plt.savefig(PROJECT_ROOT / "plot_p99_vs_rate.png", dpi=150)
plt.close()

# throughput vs rate
plt.figure(figsize=(8, 5))
plt.plot(per_rate["rate_hint"], per_rate["tps"], marker="o")
plt.xlabel("rate (messages/sec)")
plt.ylabel("throughput / tps")
plt.title("throughput vs rate")
plt.grid(True)
plt.tight_layout()
plt.savefig(PROJECT_ROOT / "plot_tps_vs_rate.png", dpi=150)
plt.close()

# p95 vs rate
plt.figure(figsize=(8, 5))
plt.plot(per_rate["rate_hint"], per_rate["p95_ms"], marker="o")
plt.xlabel("rate (messages/sec)")
plt.ylabel("p95 latency (ms)")
plt.title("p95 vs rate")
plt.grid(True)
plt.tight_layout()
plt.savefig(PROJECT_ROOT / "plot_p95_vs_rate.png", dpi=150)
plt.close()

# mean latency vs rate
plt.figure(figsize=(8, 5))
plt.plot(per_rate["rate_hint"], per_rate["mean_latency_ms"], marker="o")
plt.xlabel("rate (messages/sec)")
plt.ylabel("mean latency (ms)")
plt.title("mean latency vs rate")
plt.grid(True)
plt.tight_layout()
plt.savefig(PROJECT_ROOT / "plot_mean_latency_vs_rate.png", dpi=150)
plt.close()

# drop rate vs rate
plt.figure(figsize=(8, 5))
plt.plot(per_rate["rate_hint"], per_rate["drop_rate"], marker="o")
plt.xlabel("rate (messages/sec)")
plt.ylabel("drop rate")
plt.title("drop rate vs rate")
plt.grid(True)
plt.tight_layout()
plt.savefig(PROJECT_ROOT / "plot_drop_rate_vs_rate.png", dpi=150)
plt.close()

print("Готово.")