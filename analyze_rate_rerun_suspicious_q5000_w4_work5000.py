import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

print("SCRIPT STARTED")

PROJECT_ROOT = Path(r"C:\Users\andre\source\repos\diplom")
RUN_DIR = PROJECT_ROOT / "results" / "rate_rerun_suspicious_q5000_w4_work5000"

INPUT_CSV = RUN_DIR / "all_results_rate_rerun_suspicious_q5000_w4_work5000.csv"
OUTPUT_AGG = RUN_DIR / "rate_rerun_suspicious_q5000_w4_work5000_aggregated.csv"
OUTPUT_PER_RUN = RUN_DIR / "rate_rerun_suspicious_q5000_w4_work5000_per_run.csv"
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
    .sort_values(["rate_hint", "exp_id"])
)

print("\nАгрегация по прогонам:")
print(per_run)

per_run.to_csv(OUTPUT_PER_RUN, index=False, encoding="utf-8-sig")
print("Сохранено per_run:", OUTPUT_PER_RUN)

# Итог по rate: и медиана, и среднее, и std
per_rate = (
    per_run
    .groupby(
        ["rate_hint", "W", "Q", "mode", "batch", "batch_wait_us", "work"],
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
    .sort_values("rate_hint")
)

print("\nИтог по rate:")
print(per_rate)

per_rate.to_csv(OUTPUT_AGG, index=False, encoding="utf-8-sig")
print("Сохранено:", OUTPUT_AGG)

# ---------------------------
# Графики по медианам
# ---------------------------

plt.figure(figsize=(8, 5))
plt.plot(per_rate["rate_hint"], per_rate["tps_median"], marker="o")
plt.xlabel("input rate")
plt.ylabel("throughput / tps (median)")
plt.title("throughput vs input rate (rerun suspicious)")
plt.grid(True)
plt.tight_layout()
plt.savefig(PLOTS_DIR / "plot_tps_vs_rate_rerun.png", dpi=150)
plt.close()

plt.figure(figsize=(8, 5))
plt.plot(per_rate["rate_hint"], per_rate["mean_latency_median"], marker="o")
plt.xlabel("input rate")
plt.ylabel("mean latency (ms, median)")
plt.title("mean latency vs input rate (rerun suspicious)")
plt.grid(True)
plt.tight_layout()
plt.savefig(PLOTS_DIR / "plot_mean_latency_vs_rate_rerun.png", dpi=150)
plt.close()

plt.figure(figsize=(8, 5))
plt.plot(per_rate["rate_hint"], per_rate["p95_median"], marker="o")
plt.xlabel("input rate")
plt.ylabel("p95 latency (ms, median)")
plt.title("p95 vs input rate (rerun suspicious)")
plt.grid(True)
plt.tight_layout()
plt.savefig(PLOTS_DIR / "plot_p95_vs_rate_rerun.png", dpi=150)
plt.close()

plt.figure(figsize=(8, 5))
plt.plot(per_rate["rate_hint"], per_rate["p99_median"], marker="o")
plt.xlabel("input rate")
plt.ylabel("p99 latency (ms, median)")
plt.title("p99 vs input rate (rerun suspicious)")
plt.grid(True)
plt.tight_layout()
plt.savefig(PLOTS_DIR / "plot_p99_vs_rate_rerun.png", dpi=150)
plt.close()

plt.figure(figsize=(8, 5))
plt.plot(per_rate["rate_hint"], per_rate["queue_median"], marker="o")
plt.xlabel("input rate")
plt.ylabel("mean queue (median)")
plt.title("mean queue vs input rate (rerun suspicious)")
plt.grid(True)
plt.tight_layout()
plt.savefig(PLOTS_DIR / "plot_queue_vs_rate_rerun.png", dpi=150)
plt.close()

plt.figure(figsize=(8, 5))
plt.plot(per_rate["rate_hint"], per_rate["max_queue_median"], marker="o")
plt.xlabel("input rate")
plt.ylabel("max queue (median)")
plt.title("max queue vs input rate (rerun suspicious)")
plt.grid(True)
plt.tight_layout()
plt.savefig(PLOTS_DIR / "plot_max_queue_vs_rate_rerun.png", dpi=150)
plt.close()

plt.figure(figsize=(8, 5))
plt.plot(per_rate["rate_hint"], per_rate["drop_rate_median"], marker="o")
plt.xlabel("input rate")
plt.ylabel("drop rate (median)")
plt.title("drop rate vs input rate (rerun suspicious)")
plt.grid(True)
plt.tight_layout()
plt.savefig(PLOTS_DIR / "plot_drop_rate_vs_rate_rerun.png", dpi=150)
plt.close()

plt.figure(figsize=(8, 5))
plt.plot(per_rate["rate_hint"], per_rate["rho_eff_median"], marker="o")
plt.xlabel("input rate")
plt.ylabel("rho_eff (median)")
plt.title("rho_eff vs input rate (rerun suspicious)")
plt.grid(True)
plt.tight_layout()
plt.savefig(PLOTS_DIR / "plot_rho_eff_vs_rate_rerun.png", dpi=150)
plt.close()

# ---------------------------
# Boxplot throughput по прогонам
# ---------------------------

rates = sorted(per_run["rate_hint"].unique())
data_tps = [per_run.loc[per_run["rate_hint"] == r, "tps"].values for r in rates]

plt.figure(figsize=(9, 5))
plt.boxplot(data_tps, tick_labels=[str(r) for r in rates])
plt.xlabel("input rate")
plt.ylabel("throughput / tps per run")
plt.title("throughput distribution by rate (rerun suspicious)")
plt.grid(True)
plt.tight_layout()
plt.savefig(PLOTS_DIR / "plot_tps_boxplot_rerun.png", dpi=150)
plt.close()

# ---------------------------
# Boxplot p99 по прогонам
# ---------------------------

data_p99 = [per_run.loc[per_run["rate_hint"] == r, "p99_ms"].values for r in rates]

plt.figure(figsize=(9, 5))
plt.boxplot(data_p99, tick_labels=[str(r) for r in rates])
plt.xlabel("input rate")
plt.ylabel("p99 latency per run (ms)")
plt.title("p99 distribution by rate (rerun suspicious)")
plt.grid(True)
plt.tight_layout()
plt.savefig(PLOTS_DIR / "plot_p99_boxplot_rerun.png", dpi=150)
plt.close()

print("Готово.")
print("Графики лежат в:", PLOTS_DIR)