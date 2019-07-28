import os
import hashlib
from conans.errors import ConanInvalidConfiguration
from conans import ConanFile, CMake


class DeterministicLibConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    name = "mydetlib"
    version = "1.0"
    license = "MIT"
    exports_sources = "CMakeLists.txt", "src/mydetlib.cpp", "include/mydetlib.hpp"
    options = {"shared": [True, False],
               "fPIC": [True, False]}
    default_options = "shared=False", "fPIC=True"

    def configure(self):
        if self.settings.compiler == "Visual Studio":
            del self.options.fPIC
        elif self.options.shared:
            self.options.fPIC=True

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        self.copy("*.hpp", dst="include", src="include", keep_path=False)
        self.copy("*.lib", dst="lib",
                  src="./{}".format(self.settings.build_type), keep_path=False)
        self.copy("*.dll", dst="bin", keep_path=False)
        self.copy("*.dylib*", dst="lib", src=".", keep_path=False)
        self.copy("*.so", dst="lib", src=".", keep_path=False)
        self.copy("*.a", dst="lib", src=".", keep_path=False)
        self.copy("LICENSE", dst="licenses", src=".", keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["mydetlib"]
