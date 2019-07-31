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


def hook_output(console_txt):
    for line in console_txt.splitlines():
        if "HOOK - deterministic" in str(line):
            if "set SOURCE_DATE_EPOCH:" in str(line):
                print(Fore.CYAN + str(line, "utf-8") + Fore.RESET)
            elif "Patched file:" in str(line):
                print(Fore.CYAN + str(line, "utf-8") + Fore.RESET)
            elif "Patching".upper() in str(line).upper():
                print(Fore.CYAN + str(line, "utf-8") + Fore.RESET)


def get_binary_names(console_txt):
    paths = []
    bin_files = []
    package_folder = ""
    for line in console_txt.splitlines():
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


def set_system_rand_time():
    def _win_set_time(time_tuple):
        import win32api
        dayOfWeek = datetime(*time_tuple).isocalendar()[2]
        t = time_tuple[:2] + (dayOfWeek,) + time_tuple[2:]
        win32api.SetSystemTime(*t)
        print("System time faked: {}".format(datetime.now()))

    def _linux_set_time(time_tuple):
        import subprocess
        import shlex
        time_string = datetime(*time_tuple).isoformat()
        subprocess.call(shlex.split("sudo date -s '%s'" % time_string))
        subprocess.call(shlex.split("sudo hwclock -w"))
        print("System time faked: {}".format(datetime.now()))

    time_tuple = (random.randint(1998, 2018), random.randint(
        1, 12), 6, random.randint(0, 23), random.randint(0, 59), 0, 0,)
    if os.environ.get('TRAVIS') == 'true':
        _linux_set_time(time_tuple)
    elif os.environ.get('APPVEYOR') == 'True' and sys.platform == 'win32':
        _win_set_time(time_tuple)


class Check(object):
    def __init__(self, folder, check_args):
        self._check_args = check_args
        self._folder = folder
        self.result_deterministic = False

    def check_library_determinism(self):
        if not os.path.exists("../library/src"):
            os.mkdir("../library/src")

        binary_checksums = {}
        for check in self._check_args:
            for ref, copy_files in check.items():
                for cp_file in copy_files:
                    shutil.copy("../cases/{}".format(cp_file),
                                "../library/src/mydetlib.cpp")

                set_system_rand_time()
                out = run(
                    "cd {} && conan create . {}".format(self._folder, ref))
                bin_files = get_binary_names(out)
                hook_output(out)
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
                        self.result_deterministic = True
                        print(Fore.GREEN + Style.BRIGHT +
                              "binaries match!" + Fore.RESET + Style.RESET_ALL)


class Case(object):
    def __init__(self, name, checks, activate_hook):
        self._name = name
        self._activate_hook = activate_hook
        self._checks = checks

    def launch_case(self):
        print("\n")
        print(Fore.LIGHTMAGENTA_EX +
              "CASE: {}".format(self._name) + Fore.RESET)
        activate_deterministic_hook(self._activate_hook)
        self._checks.check_library_determinism()

    def print_result(self):
        msg = (
            Fore.GREEN + "SUCCESS") if self._checks.result_deterministic else (Fore.RED + "FAIL")
        print(Fore.LIGHTMAGENTA_EX +
              "CASE: {} ".format(self._name) + msg + Fore.RESET)


init()

checks_nothing_release = [
    {"user/channel -s build_type=Release": ["mydetlib_base.cpp"]},
    {"user/channel -s build_type=Release": ["mydetlib_base.cpp"]}
]

checks_nothing_debug = [
    {"user/channel -s build_type=Debug": ["mydetlib_base.cpp"]},
    {"user/channel -s build_type=Debug": ["mydetlib_base.cpp"]}
]

checks_date = [
    {"user/channel": ["mydetlib_macros_date.cpp"]},
    {"user/channel": ["mydetlib_macros_date.cpp"]}
]

checks_time = [
    {"user/channel": ["mydetlib_macros_time.cpp"]},
    {"user/channel": ["mydetlib_macros_time.cpp"]}
]

checks_file = [
    {"user/channel1": ["mydetlib_macros_file.cpp"]},
    {"user/channel2": ["mydetlib_macros_file.cpp"]}
]

checks_line = [
    {"user/channel": ["mydetlib_macros_line.cpp"]},
    {"user/channel": ["mydetlib_macros_line.cpp"]}
]

variation_cases = [
    Case("Empty library Release       ", Check("../library", checks_nothing_release), True),
    Case("Empty library Debug         ", Check("../library", checks_nothing_debug), True),
    Case("Library using __DATE__ macro", Check("../library", checks_date), True),
    Case("Library using __TIME__ macro", Check("../library", checks_time), True),
    Case("Library using __FILE__ macro", Check("../library", checks_file), True),
    Case("Library using __LINE__ macro", Check("../library", checks_line), True)
]

for case in variation_cases:
    case.launch_case()

for case in variation_cases:
    case.print_result()
