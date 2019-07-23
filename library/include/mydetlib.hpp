#pragma once

#include <string>

#if defined(_WIN32)
	#if defined(EXPORTDLL) || defined(LINK_STATIC_LIB)
        #define SHARED_EXPORT __declspec(dllexport)
	#elif defined(_USRDLL)
        #define SHARED_EXPORT __declspec(dllimport)
    #else
        #define SHARED_EXPORT
	#endif
#else
    #define SHARED_EXPORT
#endif

class SHARED_EXPORT MyLib
{
public:
	MyLib() = default;
	~MyLib () = default;
	void PrintMessage(const std::string& message);
};

