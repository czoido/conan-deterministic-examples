import os
import sys
import json
import shutil
import subprocess
import random
from datetime import datetime
from colorama import init, Fore, Style


def run(cmd, show=True):
    if show:
        print(cmd)

    result = ""
    try:
        result = subprocess.check_output(
            cmd, shell=True, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        result = e.output
    return result


def load(filename):
    with open(filename, "r") as f:
        return f.read()


def get_revision(console_txt):
    console_txt = str(console_txt)
    search_str = "Created package revision"
    prev = console_txt.find(search_str)
    return console_txt[prev+len(search_str)+1:-6]


def get_binary_names(console_txt):
    paths = []
    bin_files = []
    package_folder = ""
    for line in console_txt.splitlines():
        # print(line)
        binary_extensions = [".lib", ".exe", ".dll", ".a", ".so", ".dylib"]
        line = str(line)
        if any(extension in line for extension in binary_extensions):
            if "Packaged" in line and "file:" in line:
                bin_files.append(line[line.find("file:")+len("file:")+1:-1])
            elif "Linking" in line and "library" in line:
                bin_files.append(
                    line[line.find("library")+len("library")+1:-1])
        else:
            if "Linking" in line and "executable" in line:
                bin_files.append(line[line.find("bin")+len("bin")+1:-1])
        if "Package folder" in line:
            package_folder = os.path.abspath(
                line[line.find("Package folder")+len("Package folder")+1:-1])

    possible_subdirs = ["lib", "bin", "dll"]
    for subdir in possible_subdirs:
        for bin_file in bin_files:
            path = os.path.join(package_folder, subdir, bin_file)
            if os.path.isfile(path):
                paths.append(path)
    return list(set(paths))


def get_binary_checksum(filename):
    checksum = str(run("md5sum {}".format(filename), False))
    return checksum[4:36]


def activate_deterministic_hook(activate):
    if activate:
        run("conan config set hooks.deterministic-build", show=False)
        print("\n" + Fore.MAGENTA + "DETERMINISTIC HOOK " +
              Fore.CYAN + "ON" + Fore.RESET)
    else:
        run("conan config rm hooks.deterministic-build", show=False)
        print("\n" + Fore.MAGENTA + "DETERMINISTIC HOOK " +
              Fore.CYAN + "OFF" + Fore.RESET)


def check_library_determinism(path, check_list):
    binary_checksums = {}
    for ref in check_list:
        set_system_rand_time()
        out = run(
            "cd {} && conan create . {}".format(path, ref))
        bin_files = get_binary_names(out)
        for bin_file_path in bin_files:
            checksum = get_binary_checksum(bin_file_path)
            #revision = get_revision(out)
            bin_name = str(os.path.basename(bin_file_path))
            print(Fore.YELLOW + Style.BRIGHT + "Created binary: " + bin_file_path +
                  " with checksum " + checksum + Fore.RESET + Style.RESET_ALL)
            if not bin_name in binary_checksums:
                binary_checksums[bin_name] = checksum
            elif checksum not in binary_checksums[bin_name]:
                print(Fore.RED + Style.BRIGHT +
                      "binaries don't match!" + Fore.RESET + Style.RESET_ALL)
                break
            else:
                print(Fore.GREEN + Style.BRIGHT +
                      "binaries match!" + Fore.RESET + Style.RESET_ALL)

def set_system_rand_time():
    def _win_set_time(time_tuple):
        import win32api
        dayOfWeek = datetime(*time_tuple).isocalendar()[2]
        t = time_tuple[:2] + (dayOfWeek,) + time_tuple[2:]
        win32api.SetSystemTime(*t)

    def _linux_set_time(time_tuple):
        import subprocess
        import shlex
        time_string = datetime(*time_tuple).isoformat()
        # May be necessary
        # subprocess.call(shlex.split("timedatectl set-ntp false"))
        subprocess.call(shlex.split("sudo date -s '%s'" % time_string))
        subprocess.call(shlex.split("sudo hwclock -w"))

    time_tuple = (random.randint(1998, 2018), random.randint(
        1, 12), 6, random.randint(0, 23), random.randint(0, 60), 0, 0,)
    if os.environ.get('TRAVIS') == 'true':
        _linux_set_time(time_tuple)
    elif os.environ.get('APPVEYOR') == 'True' and sys.platform == 'win32':
        _win_set_time(time_tuple)
    
    print("System time faked: {}".format(datetime.now()))


class Case(object):
    def __init__(self, name, copy_files):
        self._name = name
        self._copy_files = copy_files

    def launch_case(self):
        print("\n" + Fore.YELLOW + "CASE: {}".format(self._name) + Fore.RESET)
        if not os.path.exists("../library/src"):
            os.mkdir("../library/src")
        for cp_file in self._copy_files:            
            shutil.copy("../cases/{}".format(cp_file),
                        "../library/src")

init()

# have to add specific checks for each case
# for example for __FILE__ building in different dirs
variation_cases = [
    Case("Simple library to print text",  ["mydetlib_base.cpp"]),
    Case("Example using __DATE__", ["mydetlib_macros_date.cpp"]),
    Case("Example using __TIME__", ["mydetlib_macros_date.cpp"]),
    Case("Example using __FILE__", ["mydetlib_macros_date.cpp"]),
    Case("Example using __LINE__", ["mydetlib_macros_date.cpp"])]

for case in variation_cases:

    case.launch_case()

    print("\n" + Fore.MAGENTA + "Check library reproducibility" + Fore.RESET)

    activate_deterministic_hook(False)

    print("\n" + Fore.LIGHTMAGENTA_EX +
          "Create a static library two times without changing anything" + Fore.RESET)
    check_packages = ["user/channel", "user/channel"]
    check_library_determinism("../library", check_packages)

    activate_deterministic_hook(True)

    print("\n" + Fore.LIGHTMAGENTA_EX +
          "Create a static library two times without changing anything" + Fore.RESET)
    check_packages = ["user/channel", "user/channel"]
    check_library_determinism("../library", check_packages)

"""
    print("\n" + Fore.LIGHTMAGENTA_EX +
        "Create a dynamic library two times without changing anything" + Fore.RESET)
    check_packages = ["user/channel -o shared=True", "user/channel -o shared=True"]
    check_library_determinism("../library", check_packages)

    print("\n" + Fore.LIGHTMAGENTA_EX +
        "Create a static library two times changing build directories" + Fore.RESET)
    check_packages = ["user1/channel", "user2_rand987654321/channel"]
    check_library_determinism("../library", check_packages)


    print("\n" + Fore.LIGHTMAGENTA_EX +
        "Create a dynamic library two times changing build directories" + Fore.RESET)
    check_packages = ["user1/channel -o shared=True",
                    "user2/user2_rand987654321 -o shared=True"]
    check_library_determinism("../library", check_packages)

    print("\n" + Fore.LIGHTMAGENTA_EX +
        "Create a executable two times (STATIC LIB) without changing anything" + Fore.RESET)
    check_packages = ["user/channel", "user/channel"]
    check_library_determinism("../consumer", check_packages)

    print("\n" + Fore.LIGHTMAGENTA_EX +
        "Create a executable two times (STATIC LIB) without changing build directories" + Fore.RESET)
    check_packages = ["user/channel", "user/channel"]
    check_library_determinism("../consumer", check_packages)

    print("\n" + Fore.LIGHTMAGENTA_EX +
        "Create a executable two times (DYNAMIC LIBS) without changing anything" + Fore.RESET)
    check_packages = ["user/channel -o mydetlib:shared=True",
                    "user/channel -o mydetlib:shared=True"]
    check_library_determinism("../consumer", check_packages)

    print("\n" + Fore.LIGHTMAGENTA_EX +
        "Create a executable two times (DYNAMIC LIBS) changing build directories" + Fore.RESET)
    check_packages = ["user/channel -o mydetlib:shared=True",
                    "user/user2_rand987654321 -o mydetlib:shared=True"]
    check_library_determinism("../consumer", check_packages)

"""
