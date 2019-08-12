#include "../include/mydetlib.hpp"

#include <iostream>

void MyLib::PrintMessage(const std::string & message)
{
	std::cout << message << std::endl;
	std::cout << __DATE__ << std::endl;
	std::cout << __TIME__ << std::endl;
}

