#include "../include/mydetlib.hpp"
#include "../include/sources0.hpp"
#include "../include/sources1.hpp"
#include "../include/sources2.hpp"

#include <iostream>

void MyLib::PrintMessage(const std::string & message)
{
    ClassA messageA;
    ClassB messageB;
    ClassC messageC;
	std::cout << messageA.sayHello() 
              << messageB.sayGoodBye() 
              << messageC.saySomething() 
              << message << std::endl;
}

