#pragma once
#include <string>
#include <vector>

bool isPortOpen(const std::string& ip, int port);
std::string scanPorts(const std::string& ip, const std::vector<int>& ports);
std::string guessDevice(const std::string& openPorts, const std::string& vendor);

std::string getHostname(const std::string& ip);
std::string getMAC(const std::string& ip);
std::string getVendor(const std::string& mac, const std::string& manufPath);