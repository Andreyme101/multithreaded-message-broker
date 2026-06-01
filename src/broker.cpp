#include <boost/asio.hpp>
#include <atomic>
#include <chrono>
#include <cstdint>
#include <iostream>
#include <thread>
#include <vector>
#include <algorithm>
#include <mutex>
#include <string>
#include <fstream>
#include <iomanip>
#include <optional>

#include "bounded_queue.hpp"
#include "util.hpp"
#include "net_proto.hpp"

using boost::asio::ip::tcp;

// ------------------------------
// Задача, которую воркеры берут из очереди
// ------------------------------
struct Task {
    uint64_t id;
    uint64_t send_ns;
};

// ------------------------------
// Окно статистики по latency:
// копим latency, раз в секунду делаем snapshot + reset
// ------------------------------
class StatsWindow {
public:
    explicit StatsWindow(size_t max_samples = 300000)
        : max_(max_samples) {
        v_.reserve(max_);
    }

    void add_latency_ns(uint64_t latency_ns) {
        std::lock_guard<std::mutex> lk(m_);
        if (v_.size() < max_) {
            v_.push_back(latency_ns);
        }
    }

    struct Snap {
        uint64_t n = 0;
        double mean_ms = 0.0;
        double p50_ms = 0.0;
        double p95_ms = 0.0;
        double p99_ms = 0.0;
    };

    Snap snapshot_and_reset() {
        std::vector<uint64_t> local;
        {
            std::lock_guard<std::mutex> lk(m_);
            local.swap(v_);
        }

        Snap s;
        s.n = local.size();
        if (local.empty()) {
            return s;
        }

        long double sum = 0.0;
        for (auto x : local) {
            sum += static_cast<long double>(x);
        }
        s.mean_ms = static_cast<double>(sum / static_cast<long double>(local.size()) / 1e6);

        std::sort(local.begin(), local.end());

        auto pct_ms = [&](double p) -> double {
            size_t idx = static_cast<size_t>(p * (local.size() - 1));
            return static_cast<double>(local[idx]) / 1e6;
            };

        s.p50_ms = pct_ms(0.50);
        s.p95_ms = pct_ms(0.95);
        s.p99_ms = pct_ms(0.99);
        return s;
    }

private:
    size_t max_;
    std::mutex m_;
    std::vector<uint64_t> v_;
};

// ------------------------------
// Синтетическая CPU-нагрузка.
// Это модель времени обслуживания одной задачи.
// ------------------------------
static inline void fake_work(int iters) {
    volatile uint64_t x = 0;
    for (int i = 0; i < iters; ++i) {
        x = x * 1664525u + 1013904223u;
    }
}

// ------------------------------
// Вспомогательный парсер аргументов:
// ищет пару вида: --key value
// ------------------------------
static bool get_arg(int argc, char** argv, const std::string& key, std::string& out) {
    for (int i = 1; i + 1 < argc; ++i) {
        if (argv[i] == key) {
            out = argv[i + 1];
            return true;
        }
    }
    return false;
}

int main(int argc, char** argv) {
    // ------------------------------
    // Параметры по умолчанию
    // ------------------------------
    int port = 9000;
    size_t Q = 5000;
    int W = 4;
    int work_iters = 800;
    std::string mode = "drop";   // drop | block
    int batch = 1;
    int batch_wait_us = 0;

    int duration_sec = 15;       // длительность измерения
    std::string csv_path = "";   // если пусто — CSV не пишем
    bool csv_append = false;     // false = перезаписать, true = append

    // Доп. параметры для более удобного анализа
    std::string exp_id = "exp_default";
    int rate_hint = -1;          // сюда можно передать rate producer-а, чтобы писать его в CSV

    // ------------------------------
    // Читаем аргументы командной строки
    // ------------------------------
    std::string s;
    if (get_arg(argc, argv, "--port", s)) port = std::stoi(s);
    if (get_arg(argc, argv, "--q", s)) Q = static_cast<size_t>(std::stoull(s));
    if (get_arg(argc, argv, "--w", s)) W = std::stoi(s);
    if (get_arg(argc, argv, "--work", s)) work_iters = std::stoi(s);
    if (get_arg(argc, argv, "--mode", s)) mode = s;
    if (get_arg(argc, argv, "--batch", s)) batch = std::max(1, std::stoi(s));
    if (get_arg(argc, argv, "--batch-wait-us", s)) batch_wait_us = std::max(0, std::stoi(s));

    if (get_arg(argc, argv, "--sec", s)) duration_sec = std::max(1, std::stoi(s));
    if (get_arg(argc, argv, "--csv", s)) csv_path = s;
    if (get_arg(argc, argv, "--csv-append", s)) {
        csv_append = (s == "1" || s == "true" || s == "yes");
    }
    if (get_arg(argc, argv, "--exp-id", s)) exp_id = s;
    if (get_arg(argc, argv, "--rate-hint", s)) rate_hint = std::stoi(s);

    const bool drop_mode = (mode == "drop");

    // ------------------------------
    // Печать конфигурации
    // ------------------------------
    std::cout << "BROKER CONFIG:"
        << " port=" << port
        << " W=" << W
        << " Q=" << Q
        << " mode=" << mode
        << " work=" << work_iters
        << " batch=" << batch
        << " batch_wait_us=" << batch_wait_us
        << " sec=" << duration_sec
        << " exp_id=" << exp_id
        << " rate_hint=" << rate_hint
        << " csv=" << (csv_path.empty() ? "<none>" : csv_path)
        << "\n";

    // ------------------------------
    // Основные объекты
    // ------------------------------
    BoundedQueue<Task> q(Q);
    StatsWindow stats;

    // ------------------------------
    // Глобальные счётчики
    // ------------------------------
    std::atomic<uint64_t> received{ 0 };
    std::atomic<uint64_t> processed{ 0 };
    std::atomic<uint64_t> drops{ 0 };

    std::atomic<uint64_t> service_sum_ns{ 0 };
    std::atomic<uint64_t> service_cnt{ 0 };

    std::atomic<uint64_t> max_q_size{ 0 };
    std::atomic<bool> running{ true };

    // ------------------------------
    // CSV-файл
    // ------------------------------
    std::ofstream csv;
    if (!csv_path.empty()) {
        std::ios::openmode mode_flags = std::ios::out;
        if (csv_append) {
            mode_flags |= std::ios::app;
        }

        csv.open(csv_path, mode_flags);
        if (!csv.is_open()) {
            std::cerr << "ERROR: cannot open CSV file: " << csv_path << "\n";
            return 1;
        }

        if (!csv_append) {
            csv << "exp_id,sec,rate_hint,W,Q,mode,batch,batch_wait_us,work,"
                "received,processed,drops,queue,max_queue,tps,"
                "mean_latency_ms,p50_ms,p95_ms,p99_ms,"
                "mean_service_ms,mu_per_sec,rho_eff,drop_rate\n";
        }
    }

    // ------------------------------
    // Helper: обновление max queue size
    // ------------------------------
    auto update_max_q = [&](uint64_t current_q) {
        uint64_t prev = max_q_size.load(std::memory_order_relaxed);
        while (current_q > prev &&
            !max_q_size.compare_exchange_weak(prev, current_q, std::memory_order_relaxed)) {
        }
        };

    // ------------------------------
    // Worker pool
    // ------------------------------
    std::vector<std::thread> workers;
    workers.reserve(static_cast<size_t>(W));

    for (int i = 0; i < W; ++i) {
        workers.emplace_back([&] {
            std::vector<Task> buf;
            buf.reserve(static_cast<size_t>(batch));

            while (running) {
                buf.clear();

                // Ждём хотя бы одну задачу
                auto first = q.pop_blocking();
                if (!first) {
                    break; // очередь остановлена и пуста
                }
                buf.push_back(*first);

                // Пытаемся добрать batch
                auto t_wait_start = std::chrono::steady_clock::now();
                while (static_cast<int>(buf.size()) < batch) {
                    Task tmp{};
                    if (q.try_pop(tmp)) {
                        buf.push_back(std::move(tmp));
                        continue;
                    }

                    if (batch_wait_us == 0) {
                        break;
                    }

                    auto elapsed = std::chrono::steady_clock::now() - t_wait_start;
                    if (elapsed >= std::chrono::microseconds(batch_wait_us)) {
                        break;
                    }

                    std::this_thread::sleep_for(std::chrono::microseconds(50));
                }

                // Обрабатываем batch
                for (const auto& task : buf) {
                    uint64_t t0 = now_ns();
                    fake_work(work_iters);
                    uint64_t t1 = now_ns();

                    service_sum_ns.fetch_add(t1 - t0, std::memory_order_relaxed);
                    service_cnt.fetch_add(1, std::memory_order_relaxed);

                    uint64_t latency = t1 - task.send_ns;
                    stats.add_latency_ns(latency);
                }

                processed.fetch_add(static_cast<uint64_t>(buf.size()), std::memory_order_relaxed);
            }
            });
    }

    // ------------------------------
    // Reporter thread
    // Раз в секунду пишет текущие метрики
    // ------------------------------
    std::thread reporter([&] {
        uint64_t last_processed = 0;
        uint64_t last_service_sum = 0;
        uint64_t last_service_cnt = 0;

        for (int sec_idx = 1; sec_idx <= duration_sec && running; ++sec_idx) {
            std::this_thread::sleep_for(std::chrono::seconds(1));

            auto snap = stats.snapshot_and_reset();

            uint64_t p_total = processed.load(std::memory_order_relaxed);
            uint64_t tps = p_total - last_processed;
            last_processed = p_total;

            uint64_t ss = service_sum_ns.load(std::memory_order_relaxed);
            uint64_t sc = service_cnt.load(std::memory_order_relaxed);

            uint64_t ss_delta = ss - last_service_sum;
            uint64_t sc_delta = sc - last_service_cnt;

            last_service_sum = ss;
            last_service_cnt = sc;

            double mean_service_ms = 0.0;
            if (sc_delta > 0) {
                mean_service_ms = static_cast<double>(ss_delta) / static_cast<double>(sc_delta) / 1e6;
            }

            double mu = 0.0;
            if (mean_service_ms > 0.0) {
                double s_sec = mean_service_ms / 1000.0;
                mu = 1.0 / s_sec;
            }

            // Эффективная интенсивность = сколько реально обработали за секунду
            double lambda_eff = static_cast<double>(tps);
            double rho_eff = (mu > 0.0) ? (lambda_eff / (static_cast<double>(W) * mu)) : 0.0;

            uint64_t recv_now = received.load(std::memory_order_relaxed);
            uint64_t drop_now = drops.load(std::memory_order_relaxed);
            uint64_t q_now = q.size();
            uint64_t max_q_now = max_q_size.load(std::memory_order_relaxed);

            double drop_rate = 0.0;
            if (recv_now > 0) {
                drop_rate = static_cast<double>(drop_now) / static_cast<double>(recv_now);
            }

            std::cout << "[1s #" << sec_idx << "]"
                << " tps=" << tps
                << " recv=" << recv_now
                << " drops=" << drop_now
                << " q=" << q_now
                << " maxQ=" << max_q_now
                << " meanLat=" << snap.mean_ms << "ms"
                << " p50=" << snap.p50_ms << "ms"
                << " p95=" << snap.p95_ms << "ms"
                << " p99=" << snap.p99_ms << "ms"
                << " | meanS=" << mean_service_ms << "ms"
                << " mu~=" << mu << "/s"
                << " rho_eff~=" << rho_eff
                << " dropRate=" << (drop_rate * 100.0) << "%"
                << "\n";

            if (csv.is_open()) {
                csv << exp_id << ","
                    << sec_idx << ","
                    << rate_hint << ","
                    << W << ","
                    << Q << ","
                    << mode << ","
                    << batch << ","
                    << batch_wait_us << ","
                    << work_iters << ","
                    << recv_now << ","
                    << p_total << ","
                    << drop_now << ","
                    << q_now << ","
                    << max_q_now << ","
                    << tps << ","
                    << std::fixed << std::setprecision(6)
                    << snap.mean_ms << ","
                    << snap.p50_ms << ","
                    << snap.p95_ms << ","
                    << snap.p99_ms << ","
                    << mean_service_ms << ","
                    << mu << ","
                    << rho_eff << ","
                    << drop_rate
                    << "\n";
            }
        }

        // Когда время измерения вышло — останавливаем систему
        running = false;
        q.stop();
        });

    // ------------------------------
    // Сетевая часть: принимаем 1 клиента и читаем поток сообщений
    // ------------------------------
    try {
        boost::asio::io_context io;
        tcp::acceptor acceptor(io, tcp::endpoint(tcp::v4(), port));

        std::cout << "Listening on port " << port << "\n";

        tcp::socket sock(io);
        acceptor.accept(sock);

        std::cout << "Client connected: " << sock.remote_endpoint() << "\n";

        while (running) {
            NetMsg m{};
            boost::system::error_code ec;

            size_t n = boost::asio::read(sock, boost::asio::buffer(&m, sizeof(m)), ec);

            if (ec) {
                if (running) {
                    std::cout << "Network stopped: " << ec.message() << "\n";
                }
                break;
            }

            if (n != sizeof(m)) {
                std::cout << "Network stopped: partial read\n";
                break;
            }

            Task t{ m.id, m.send_ns };
            received.fetch_add(1, std::memory_order_relaxed);

            if (drop_mode) {
                if (!q.try_push(std::move(t))) {
                    drops.fetch_add(1, std::memory_order_relaxed);
                }
                else {
                    update_max_q(q.size());
                }
            }
            else {
                q.push_blocking(std::move(t));
                update_max_q(q.size());
            }
        }
    }
    catch (const std::exception& e) {
        std::cout << "Network stopped: " << e.what() << "\n";
    }

    // ------------------------------
    // Корректное завершение
    // ------------------------------
    running = false;
    q.stop();

    for (auto& th : workers) {
        if (th.joinable()) {
            th.join();
        }
    }

    if (reporter.joinable()) {
        reporter.join();
    }

    // ------------------------------
    // Финальная summary
    // ------------------------------
    uint64_t recv_total = received.load(std::memory_order_relaxed);
    uint64_t proc_total = processed.load(std::memory_order_relaxed);
    uint64_t drop_total = drops.load(std::memory_order_relaxed);
    uint64_t max_q_total = max_q_size.load(std::memory_order_relaxed);
    uint64_t sc_total = service_cnt.load(std::memory_order_relaxed);
    uint64_t ss_total = service_sum_ns.load(std::memory_order_relaxed);

    double mean_service_ms_total = 0.0;
    if (sc_total > 0) {
        mean_service_ms_total = static_cast<double>(ss_total) / static_cast<double>(sc_total) / 1e6;
    }

    double avg_tps = (duration_sec > 0)
        ? (static_cast<double>(proc_total) / static_cast<double>(duration_sec))
        : 0.0;

    double drop_rate_total = (recv_total > 0)
        ? (static_cast<double>(drop_total) / static_cast<double>(recv_total))
        : 0.0;

    double mu_total = 0.0;
    if (mean_service_ms_total > 0.0) {
        mu_total = 1.0 / (mean_service_ms_total / 1000.0);
    }

    double rho_eff_total = (mu_total > 0.0)
        ? (avg_tps / (static_cast<double>(W) * mu_total))
        : 0.0;

    std::cout << "\n===== FINAL SUMMARY =====\n";
    std::cout << "exp_id=" << exp_id << "\n";
    std::cout << "received_total=" << recv_total << "\n";
    std::cout << "processed_total=" << proc_total << "\n";
    std::cout << "drops_total=" << drop_total << "\n";
    std::cout << "drop_rate_total=" << (drop_rate_total * 100.0) << "%\n";
    std::cout << "avg_tps=" << avg_tps << "\n";
    std::cout << "max_queue_size=" << max_q_total << "\n";
    std::cout << "mean_service_ms_total=" << mean_service_ms_total << "\n";
    std::cout << "mu_total=" << mu_total << "/s\n";
    std::cout << "rho_eff_total=" << rho_eff_total << "\n";
    std::cout << "=========================\n";

    if (csv.is_open()) {
        csv.flush();
        csv.close();
    }

    return 0;
}