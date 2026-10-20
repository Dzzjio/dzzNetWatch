#include <iostream>
#include <cstdlib>
#include <string>
#include <vector>
#include <thread>
#include <atomic>
#include <chrono>
#include <unistd.h>
#include <arpa/inet.h>
#include "scanner.h"

void spinner(const std::string& ip, std::atomic<bool>& running) {
    const char frames[] = {'|', '/', '-', '\\'};
    int i = 0;
    while (running) {
        std::cout << "\r  " << frames[i % 4] << "  scanning " << ip << "   " << std::flush;
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
        i++;
    }
}

int main(int argc, char* argv[]) {
    // defaults — hotspot
    std::string base      = "172.20.10.";
    int startIP           = 1;
    int endIP             = 14;
    std::string manufPath = "../manuf.txt";

    // if Python passes subnet args, use those instead
    // usage: ./netwatch <base> <start> <end> [manuf path]
    // e.g.:  ./netwatch 192.168.1. 1 254
    if (argc == 4 || argc == 5) {
        base = argv[1];
        try {
            startIP = std::stoi(argv[2]);
            endIP   = std::stoi(argv[3]);
        } catch (...) {
            std::cerr << "invalid range: " << argv[2] << " " << argv[3] << "\n";
            return 1;
        }
        if (argc == 5) manufPath = argv[4];
    } else if (argc != 1) {
        std::cerr << "usage: " << argv[0] << " <base> <start> <end> [manuf path]\n";
        return 1;
    }

    // base goes into a shell command below, so it must be a real "a.b.c." prefix
    struct in_addr tmp;
    if (base.empty() || base.back() != '.' ||
        inet_pton(AF_INET, (base + "0").c_str(), &tmp) != 1) {
        std::cerr << "invalid base: " << base << " (expected e.g. 192.168.1.)\n";
        return 1;
    }
    if (startIP < 0 || endIP > 255 || startIP > endIP) {
        std::cerr << "invalid range: " << startIP << "-" << endIP << " (must be within 0-255)\n";
        return 1;
    }

    // only animate when a human is watching; Python captures stdout
    bool interactive = isatty(STDOUT_FILENO);

    std::vector<int> ports = {22, 80, 135, 443, 445, 3306, 7000, 9100, 62078};

    std::cout << "\nNetWatch — scanning " << base << "0\n";
    std::cout << "─────────────────────────────────────────────────────\n";

    int found = 0;

    for (int i = startIP; i <= endIP; i++) {
        std::string ip = base + std::to_string(i);

        std::atomic<bool> running(interactive);
        std::thread spinThread;
        if (interactive) spinThread = std::thread(spinner, ip, std::ref(running));

        std::string cmd = "ping -c 1 -W 1 " + ip + " > /dev/null 2>&1";
        int result = std::system(cmd.c_str());

        std::string hostname, mac, vendor, openPorts, device;
        if (result == 0) {
            hostname  = getHostname(ip);
            mac       = getMAC(ip);
            vendor    = getVendor(mac, manufPath);
            openPorts = scanPorts(ip, ports);
            device    = guessDevice(openPorts, vendor);
            found++;
        }

        if (interactive) {
            running = false;
            spinThread.join();
            std::cout << "\r                                                     \r" << std::flush;
        }

        if (result == 0) {
            std::cout << "  ✓  " << ip
                      << "\n       hostname : " << hostname
                      << "\n       device   : " << device
                      << "\n       mac      : " << mac
                      << "\n       vendor   : " << vendor
                      << "\n       ports    : " << openPorts
                      << "\n" << std::endl;
        }
    }

    std::cout << "─────────────────────────────────────────────────────\n";
    std::cout << "Scan complete. " << found << " device(s) found.\n\n";

    return 0;
}