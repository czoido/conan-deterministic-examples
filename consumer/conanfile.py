from conans import ConanFile, CMake


class DetlibConsumerConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    requires = "mydetlib/1.0@user/channel"
    generators = "cmake"
    name = "mydetlibconsumer"
    version = "1.0"
    exports_sources = "CMakeLists.txt", "src/main.cpp"

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        self.copy("*consumer.exe", dst="bin", keep_path=False)
        self.copy("*consumer", dst="bin", keep_path=False)
