#include "../include/mydetlib.hpp"

#include <iostream>

struct example_structure {
	uint32_t field1;
	uint16_t field2;
	uint32_t field3;
	uint16_t field4;
};

void MyLib::PrintMessage(const std::string & message)
{
    struct example_structure my_structure = {0};
	std::cout << message << std::endl;
}

