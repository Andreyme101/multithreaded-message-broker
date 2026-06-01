#pragma once

#include <condition_variable>
#include <deque>
#include <mutex>
#include <optional>
#include <utility>

template <class T>
class BoundedQueue {
public:
    explicit BoundedQueue(size_t capacity)
        : cap_(capacity) {
    }

    // BLOCK: ждём, если очередь заполнена
    void push_blocking(T item) {
        std::unique_lock<std::mutex> lock(m_);
        cv_not_full_.wait(lock, [&] { return q_.size() < cap_ || stopped_; });
        if (stopped_) return;

        q_.push_back(std::move(item));
        cv_not_empty_.notify_one();
    }

    // DROP: если заполнена — возвращаем false
    bool try_push(T item) {
        std::lock_guard<std::mutex> lock(m_);
        if (stopped_) return false;
        if (q_.size() >= cap_) return false;

        q_.push_back(std::move(item));
        cv_not_empty_.notify_one();
        return true;
    }

    // BLOCK pop: ждём элемент; если stop() и пусто — nullopt
    std::optional<T> pop_blocking() {
        std::unique_lock<std::mutex> lock(m_);
        cv_not_empty_.wait(lock, [&] { return !q_.empty() || stopped_; });

        if (q_.empty()) return std::nullopt;

        T item = std::move(q_.front());
        q_.pop_front();
        cv_not_full_.notify_one();
        return item;
    }

    // Non-blocking pop: если пусто — false
    bool try_pop(T& out) {
        std::lock_guard<std::mutex> lock(m_);
        if (stopped_) return false;
        if (q_.empty()) return false;

        out = std::move(q_.front());
        q_.pop_front();
        cv_not_full_.notify_one();
        return true;
    }

    void stop() {
        std::lock_guard<std::mutex> lock(m_);
        stopped_ = true;
        cv_not_empty_.notify_all();
        cv_not_full_.notify_all();
    }

    size_t size() const {
        std::lock_guard<std::mutex> lock(m_);
        return q_.size();
    }

private:
    const size_t cap_;
    mutable std::mutex m_;
    std::condition_variable cv_not_empty_;
    std::condition_variable cv_not_full_;
    std::deque<T> q_;
    bool stopped_ = false;
};