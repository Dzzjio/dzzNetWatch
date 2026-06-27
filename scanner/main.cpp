#include <iostream>
#include <cstdlib>
#include <string>
#include <vector>
#include <thread>
#include <atomic>
#include <chrono>
#include "scanner.h"

// ─────────────────────────────────────────────
// LOADER ANIMATION
// ─────────────────────────────────────────────
// runs in a separate thread while ping + port scan is happening.
// atomic<bool> is thread-safe — one thread writes it, one reads it,
// no risk of them stepping on each other.
// ─────────────────────────────────────────────
void spinner(const std::string& ip, std::atomic<bool>& running) {
    const char frames[] = {'|', '/', '-', '\\'};
    int i = 0;
    while (running) {
        std::cout << "\r  " << frames[i % 4] << "  scanning " << ip << "   " << std::flush;
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
        i++;
    }
}

int main() {
    std::string base      = "172.20.10.";
    std::string manufPath = "../manuf.txt";

    // ports to check on each device
    std::vector<int> ports = {22, 80, 443, 3306, 7000, 9100, 62078};

    std::cout << "\nNetWatch — scanning " << base << "0/28\n";
    std::cout << "─────────────────────────────────────────────────────\n";

    int found = 0;

    for (int i = 1; i <= 14; i++) {
        std::string ip = base + std::to_string(i);

        // start spinner in background thread while we ping + scan
        std::atomic<bool> running(true);
        std::thread spinThread(spinner, ip, std::ref(running));

        // step 1: ping to check if host is alive
        std::string cmd = "ping -c 1 -W 1 " + ip + " > /dev/null 2>&1";
        int result = std::system(cmd.c_str());

        // step 2: if alive, gather info (ports take a few seconds)
        std::string hostname, mac, vendor, openPorts, device;
        if (result == 0) {
            hostname  = getHostname(ip);
            mac       = getMAC(ip);
            vendor    = getVendor(mac, manufPath);
            openPorts = scanPorts(ip, ports);
            device    = guessDevice(openPorts, vendor);
            found++;
        }

        // stop spinner before printing result
        running = false;
        spinThread.join();

        // clear spinner line
        std::cout << "\r                                                     \r" << std::flush;

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