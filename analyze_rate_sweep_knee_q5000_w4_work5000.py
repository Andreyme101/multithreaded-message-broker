import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

print("SCRIPT STARTED")

PROJECT_ROOT = Path(r"C:\Users\andre\source\repos\diplom")
RUN_DIR = PROJECT_ROOT / "results" / "rate_sweep_knee_q5000_w4_work5000"

INPUT_CSV = RUN_DIR / "all_results_rate_sweep_knee_q5000_w4_work5000.csv"
OUTPUT_AGG = RUN_DIR / "rate_sweep_knee_q5000_w4_work5000_aggregated.csv"
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

# Агрегация по rate
per_rate = (
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
    .sort_values("rate_hint")
)

print("\nИтог по rate:")
print(per_rate)

per_rate.to_csv(OUTPUT_AGG, index=False, encoding="utf-8-sig")
print("Сохранено:", OUTPUT_AGG)

# -------- графики --------

# throughput vs rate
plt.figure(figsize=(8, 5))
plt.plot(per_rate["rate_hint"], per_rate["tps"], marker="o")
plt.xlabel("input rate")
plt.ylabel("throughput / tps")
plt.title("throughput vs input rate (knee sweep)")
plt.grid(True)
plt.tight_layout()
plt.savefig(PLOTS_DIR / "plot_tps_vs_rate_knee.png", dpi=150)
plt.close()

# mean latency vs rate
plt.figure(figsize=(8, 5))
plt.plot(per_rate["rate_hint"], per_rate["mean_latency_ms"], marker="o")
plt.xlabel("input rate")
plt.ylabel("mean latency (ms)")
plt.title("mean latency vs input rate (knee sweep)")
plt.grid(True)
plt.tight_layout()
plt.savefig(PLOTS_DIR / "plot_mean_latency_vs_rate_knee.png", dpi=150)
plt.close()

# p95 vs rate
plt.figure(figsize=(8, 5))
plt.plot(per_rate["rate_hint"], per_rate["p95_ms"], marker="o")
plt.xlabel("input rate")
plt.ylabel("p95 latency (ms)")
plt.title("p95 vs input rate (knee sweep)")
plt.grid(True)
plt.tight_layout()
plt.savefig(PLOTS_DIR / "plot_p95_vs_rate_knee.png", dpi=150)
plt.close()

# p99 vs rate
plt.figure(figsize=(8, 5))
plt.plot(per_rate["rate_hint"], per_rate["p99_ms"], marker="o")
plt.xlabel("input rate")
plt.ylabel("p99 latency (ms)")
plt.title("p99 vs input rate (knee sweep)")
plt.grid(True)
plt.tight_layout()
plt.savefig(PLOTS_DIR / "plot_p99_vs_rate_knee.png", dpi=150)
plt.close()

# mean queue vs rate
plt.figure(figsize=(8, 5))
plt.plot(per_rate["rate_hint"], per_rate["queue"], marker="o")
plt.xlabel("input rate")
plt.ylabel("mean queue")
plt.title("mean queue vs input rate (knee sweep)")
plt.grid(True)
plt.tight_layout()
plt.savefig(PLOTS_DIR / "plot_queue_vs_rate_knee.png", dpi=150)
plt.close()

# max queue vs rate
plt.figure(figsize=(8, 5))
plt.plot(per_rate["rate_hint"], per_rate["max_queue"], marker="o")
plt.xlabel("input rate")
plt.ylabel("max queue")
plt.title("max queue vs input rate (knee sweep)")
plt.grid(True)
plt.tight_layout()
plt.savefig(PLOTS_DIR / "plot_max_queue_vs_rate_knee.png", dpi=150)
plt.close()

# drop rate vs rate
plt.figure(figsize=(8, 5))
plt.plot(per_rate["rate_hint"], per_rate["drop_rate"], marker="o")
plt.xlabel("input rate")
plt.ylabel("drop rate")
plt.title("drop rate vs input rate (knee sweep)")
plt.grid(True)
plt.tight_layout()
plt.savefig(PLOTS_DIR / "plot_drop_rate_vs_rate_knee.png", dpi=150)
plt.close()

# rho_eff vs rate
plt.figure(figsize=(8, 5))
plt.plot(per_rate["rate_hint"], per_rate["rho_eff"], marker="o")
plt.xlabel("input rate")
plt.ylabel("rho_eff")
plt.title("rho_eff vs input rate (knee sweep)")
plt.grid(True)
plt.tight_layout()
plt.savefig(PLOTS_DIR / "plot_rho_eff_vs_rate_knee.png", dpi=150)
plt.close()

print("Готово.")
print("Графики лежат в:", PLOTS_DIR)