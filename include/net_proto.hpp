#pragma once
#include <cstdint>

// Мини-протокол: одно сообщение = (id, timestamp отправки)
#pragma pack(push, 1)
struct NetMsg {
    uint64_t id;
    uint64_t send_ns;
};
#pragma pack(pop)