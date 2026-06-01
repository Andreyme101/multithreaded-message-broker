#include <boost/asio.hpp>
#include <chrono>
#include <cstdint>
#include <iostream>
#include <thread>
#include <string>
#include <algorithm>
#include <exception>

#include "util.hpp"
#include "net_proto.hpp"

using boost::asio::ip::tcp;

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
    try {
        std::string host = "127.0.0.1";
        int port = 9000;
        int rate = 20000;
        int duration_sec = 10;

        std::string s;
        if (get_arg(argc, argv, "--host", s)) host = s;
        if (get_arg(argc, argv, "--port", s)) port = std::stoi(s);
        if (get_arg(argc, argv, "--rate", s)) rate = std::stoi(s);
        if (get_arg(argc, argv, "--sec", s)) duration_sec = std::stoi(s);

        std::cout << "PRODUCER CONFIG: host=" << host
            << " port=" << port
            << " rate=" << rate
            << " sec=" << duration_sec
            << "\n";

        boost::asio::io_context io;
        tcp::socket sock(io);

        boost::system::error_code ec;

        auto addr = boost::asio::ip::make_address(host, ec);
        if (ec) {
            std::cerr << "Address parse error: " << ec.message() << "\n";
            return 1;
        }

        sock.connect(tcp::endpoint(addr, port), ec);
        if (ec) {
            std::cerr << "Connect error: " << ec.message() << "\n";
            return 1;
        }

        std::cout << "Connected\n";

        uint64_t id = 0;
        auto start = std::chrono::steady_clock::now();
        auto next = start;
        auto period = std::chrono::nanoseconds(
            static_cast<long long>(1e9 / std::max(1, rate))
        );

        while (std::chrono::steady_clock::now() - start < std::chrono::seconds(duration_sec)) {
            NetMsg m;
            m.id = id++;
            m.send_ns = now_ns();

            ec.clear();
            size_t written = boost::asio::write(sock, boost::asio::buffer(&m, sizeof(m)), ec);

            if (ec) {
                std::cout << "Write stopped: " << ec.message() << "\n";
                break;
            }

            if (written != sizeof(m)) {
                std::cout << "Write stopped: partial write\n";
                break;
            }

            next += period;
            std::this_thread::sleep_until(next);
        }

        ec.clear();
        sock.shutdown(tcp::socket::shutdown_both, ec);
        ec.clear();
        sock.close(ec);

        std::cout << "Done. sent=" << id << "\n";
        return 0;
    }
    catch (const std::exception& e) {
        std::cerr << "Producer std::exception: " << e.what() << "\n";
        return 1;
    }
    catch (...) {
        std::cerr << "Producer unknown fatal error\n";
        return 1;
    }
}