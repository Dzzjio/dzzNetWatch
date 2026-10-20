#include "scanner.h"
#include <unistd.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <sys/socket.h>
#include <netdb.h>
#include <ifaddrs.h>
#include <cstring>
#include <fstream>
#include <sstream>
#include <algorithm>
#include <string>
#include <vector>

std::string getHostname(const std::string& ip) {
    struct sockaddr_in sa;
    std::memset(&sa, 0, sizeof(sa));
    sa.sin_family = AF_INET;
    if (inet_pton(AF_INET, ip.c_str(), &sa.sin_addr) != 1) return "unknown";
    char host[256];
    // NI_NAMEREQD: fail instead of silently returning the numeric IP
    int result = getnameinfo((struct sockaddr*)&sa, sizeof(sa),
                              host, sizeof(host), nullptr, 0, NI_NAMEREQD);
    if (result == 0) return std::string(host);
    return "unknown";
}

std::string getMAC(const std::string& ip) {
    std::ifstream arp("/proc/net/arp");
    std::string line;
    std::getline(arp, line);
    while (std::getline(arp, line)) {
        std::istringstream iss(line);
        std::string addr, hwtype, flags, mac;
        iss >> addr >> hwtype >> flags >> mac;
        // flags 0x0 = incomplete entry (no reply), MAC is all zeros
        if (addr == ip && flags != "0x0" && mac != "00:00:00:00:00:00") return mac;
    }
    // not in the ARP table — maybe it's one of our own interfaces
    struct ifaddrs* ifs = nullptr;
    if (getifaddrs(&ifs) != 0) return "unknown";
    std::string ifname;
    for (struct ifaddrs* it = ifs; it; it = it->ifa_next) {
        if (!it->ifa_addr || it->ifa_addr->sa_family != AF_INET) continue;
        char buf[INET_ADDRSTRLEN];
        auto* sin = (struct sockaddr_in*)it->ifa_addr;
        inet_ntop(AF_INET, &sin->sin_addr, buf, sizeof(buf));
        if (ip == buf) { ifname = it->ifa_name; break; }
    }
    freeifaddrs(ifs);
    if (ifname.empty()) return "unknown";
    std::ifstream self("/sys/class/net/" + ifname + "/address");
    std::string selfMac;
    if (self.is_open() && std::getline(self, selfMac) && !selfMac.empty()) return selfMac;
    return "unknown";
}

static std::string trim(const std::string& s) {
    size_t b = s.find_first_not_of(" \t\r\n");
    if (b == std::string::npos) return "";
    size_t e = s.find_last_not_of(" \t\r\n");
    return s.substr(b, e - b + 1);
}

// supports both the IEEE oui.txt format ("28-6F-B9   (hex)\t\tNokia ...")
// and the Wireshark manuf format ("00:00:01\tXerox\tXerox Corporation")
std::string getVendor(const std::string& mac, const std::string& manufPath) {
    if (mac == "unknown" || mac.size() < 8) return "unknown";
    std::string oui = mac.substr(0, 8);
    std::transform(oui.begin(), oui.end(), oui.begin(), ::toupper);
    std::replace(oui.begin(), oui.end(), '-', ':');
    std::ifstream manuf(manufPath);
    if (!manuf.is_open()) return "no-db";
    std::string line;
    while (std::getline(manuf, line)) {
        if (line.size() < 8 || line[0] == '#') continue;
        std::string prefix = line.substr(0, 8);
        std::transform(prefix.begin(), prefix.end(), prefix.begin(), ::toupper);
        std::replace(prefix.begin(), prefix.end(), '-', ':');
        if (prefix != oui) continue;
        // skip longer (MA-M / MA-S) prefixes like "00:1B:C5:00:00:00/36"
        if (line.size() > 8 && line[8] != ' ' && line[8] != '\t') continue;

        std::string name;
        size_t hex = line.find("(hex)");
        if (hex != std::string::npos) {
            name = trim(line.substr(hex + 5));
        } else {
            std::vector<std::string> fields;
            std::istringstream iss(line);
            std::string field;
            while (std::getline(iss, field, '\t')) fields.push_back(trim(field));
            if (fields.size() >= 3 && !fields[2].empty()) name = fields[2];
            else if (fields.size() >= 2) name = fields[1];
        }
        return name.empty() ? "unknown" : name;
    }
    return "unknown";
}

bool isPortOpen(const std::string& ip, int port) {
    int sock = socket(AF_INET, SOCK_STREAM, 0);
    if (sock < 0) return false;
    struct timeval tv = {1, 0};
    setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));
    setsockopt(sock, SOL_SOCKET, SO_SNDTIMEO, &tv, sizeof(tv));
    struct sockaddr_in addr;
    std::memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_port = htons(port);
    if (inet_pton(AF_INET, ip.c_str(), &addr.sin_addr) != 1) {
        close(sock);
        return false;
    }
    bool open = connect(sock, (struct sockaddr*)&addr, sizeof(addr)) == 0;
    close(sock);
    return open;
}

std::string scanPorts(const std::string& ip, const std::vector<int>& ports) {
    std::string result = "";
    for (int port : ports) {
        if (isPortOpen(ip, port)) {
            if (!result.empty()) result += ",";
            result += std::to_string(port);
        }
    }
    return result.empty() ? "none" : result;
}

std::string guessDevice(const std::string& openPorts, const std::string& vendor) {
    // match whole port numbers, not substrings ("80" must not match "8080")
    std::vector<int> open;
    std::istringstream iss(openPorts);
    std::string tok;
    while (std::getline(iss, tok, ',')) {
        try { open.push_back(std::stoi(tok)); } catch (...) {}
    }
    auto has = [&](int p) { return std::find(open.begin(), open.end(), p) != open.end(); };

    if (has(62078)) return "iPhone";
    if (has(7000))  return "Apple device";
    if (has(9100))  return "Printer";
    if (has(3306))  return "Database server";
    if (has(135) || has(445)) return "Windows machine";
    if (has(22))    return "Linux/Mac machine";
    if (has(80) || has(443)) return "Router/Web server";
    if (vendor.find("Apple")    != std::string::npos) return "Apple device";
    if (vendor.find("Intel")    != std::string::npos) return "PC/Laptop";
    if (vendor.find("Samsung")  != std::string::npos) return "Samsung device";
    return "unknown device";
}
