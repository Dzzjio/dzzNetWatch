#include <iostream>
#include <cstdlib>
#include <string>

int main() {
    std::string base = "172.20.10.";
    
    for (int i = 1; i <= 14; i++) {
        std::string ip = base + std::to_string(i);
        std::string cmd = "ping -c 1 -W 1 " + ip + " > /dev/null 2>&1";
        int result = std::system(cmd.c_str());
        
        if (result == 0) {
            std::cout << ip << " online" << std::endl;
        }
    }
    return 0;
}