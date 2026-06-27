#include "scanner.h"
#include <unistd.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <sys/socket.h>
#include <netdb.h>
#include <fstream>
#include <sstream>
#include <algorithm>
#include <string>
#include <vector>

std::string getHostname(const std::string& ip) {
    struct sockaddr_in sa;
    sa.sin_family = AF_INET;
    inet_pton(AF_INET, ip.c_str(), &sa.sin_addr);
    char host[256];
    int result = getnameinfo((struct sockaddr*)&sa, sizeof(sa),
                              host, sizeof(host), nullptr, 0, 0);
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
        if (addr == ip) return mac;
    }
    std::ifstream self("/sys/class/net/wlo1/address");
    if (self.is_open()) {
        std::string mac;
        std::getline(self, mac);
        return mac;
    }
    return "unknown";
}

std::string getVendor(const std::string& mac, const std::string& manufPath) {
    if (mac == "unknown") return "unknown";
    std::string oui = mac.substr(0, 8);
    std::transform(oui.begin(), oui.end(), oui.begin(), ::toupper);
    std::ifstream manuf(manufPath);
    if (!manuf.is_open()) return "no-db";
    std::string line;
    while (std::getline(manuf, line)) {
        if (line.empty() || line[0] == '#') continue;
        if (line.substr(0, 8) == oui) {
            std::istringstream iss(line);
            std::string prefix, shortname;
            iss >> prefix >> shortname;
            return shortname.empty() ? "unknown" : shortname;
        }
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
    addr.sin_family = AF_INET;
    addr.sin_port = htons(port);
    inet_pton(AF_INET, ip.c_str(), &addr.sin_addr);
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
    if (openPorts.find("62078") != std::string::npos) return "iPhone";
    if (openPorts.find("7000")  != std::string::npos) return "Apple device";
    if (openPorts.find("9100")  != std::string::npos) return "Printer";
    if (openPorts.find("3306")  != std::string::npos) return "Database server";
    if (openPorts.find("22")    != std::string::npos) return "Linux/Mac machine"; 
    if (openPorts.find("80")    != std::string::npos) return "Router/Web server";
    if (vendor.find("Apple")    != std::string::npos) return "Apple device";
    if (vendor.find("Intel")    != std::string::npos) return "PC/Laptop";
    if (vendor.find("Samsung")  != std::string::npos) return "Samsung device";
    return "unknown device";
}
