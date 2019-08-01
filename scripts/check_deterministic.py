import json
import os
import random
import shutil
import subprocess
import sys
from datetime import datetime

from colorama import Fore, Style, init


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

def get_compiler(console_txt):
    for line in console_txt.splitlines():
        line = str(line)
        if "compiler=" in line:
            comp_pos = line.find("compiler=")
            return line[comp_pos+len("compiler="):-1]
    return ""

def hook_output(console_txt):
    for line in console_txt.splitlines():
        if "HOOK - deterministic" in str(line):
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

compiler = ""

class Check(object):
    def __init__(self, checks):
        self._checks = checks

    def check_library_determinism(self, hook_state):
        activate_deterministic_hook(hook_state)
        binary_checksums = {}
        for check in self._checks:
            # copy new source files
            for src, dst in check["sources"].items():
                path = os.path.dirname(dst)
                if not os.path.exists(path):
                    os.mkdir(path)
                shutil.copy(src, dst)

            folder = check["folder"]
            command = check["command"]

            set_system_rand_time()

            out = run(
                "cd {} && conan create . {}".format(folder, command))
            # have to change
            compiler = get_compiler(out)
            bin_files = get_binary_names(out)
            hook_output(out)
            for bin_file_path in bin_files:
                checksum = get_binary_checksum(bin_file_path)
                #revision = get_revision(out)
                bin_name = str(os.path.basename(bin_file_path))
                print(Fore.YELLOW + Style.BRIGHT + "Created binary: " + bin_file_path +
                      " with checksum " + checksum + Fore.RESET + Style.RESET_ALL)
                if not bin_name in binary_checksums:
                    binary_checksums[bin_name] = {
                        "checksum": checksum, "fail": False}
                elif checksum not in binary_checksums[bin_name]["checksum"]:
                    print(Fore.RED + Style.BRIGHT +
                          "binaries don't match!" + Fore.RESET + Style.RESET_ALL)
                    binary_checksums[bin_name]["fail"] = True
                else:
                    print(Fore.GREEN + Style.BRIGHT +
                          "binaries match!" + Fore.RESET + Style.RESET_ALL)
                    binary_checksums[bin_name]["fail"] = False

        for _, data in binary_checksums.items():
            if data["fail"]:
                return hook_state, False
            else:
                return hook_state, True


class Case(object):
    def __init__(self, name, checks, activate_hook):
        self.name = name
        self._checks = Check(checks)
        self._activate_hook = activate_hook

    def launch_case(self):
        print("\n")
        print(Fore.LIGHTMAGENTA_EX +
              "CASE: {}".format(self.name) + Fore.RESET)
        return self._checks.check_library_determinism(self._activate_hook)


def print_results(results):
    header_justify_s = 10
    header_justify_l = 45
    print(Fore.LIGHTMAGENTA_EX +
          "".ljust(header_justify_l) + "HOOK OFF".ljust(header_justify_s) + "HOOK ON".ljust(header_justify_s) + Fore.RESET)
    result_msg = {
        None: Fore.WHITE + "UNKNOWN".ljust(header_justify_s),
        False: Fore.RED + "FAIL".ljust(header_justify_s),
        True: Fore.GREEN + "SUCCESS".ljust(header_justify_s)
    }
    for case_name, result in results.items():
        msg_hook_on = result_msg[result[True]]
        msg_hook_off = result_msg[result[False]]
        print(Fore.LIGHTMAGENTA_EX +
              "CASE: {} ".format(case_name).ljust(header_justify_l) + msg_hook_off + msg_hook_on + Fore.RESET)


init()

checks_nothing_release = [
    {
        "command": "user/channel -s build_type=Release",
        "folder": "../library",
        "sources":  {
            "../cases/mydetlib_base.cpp": "../library/src/mydetlib.cpp",
            "../cases/CMakeListsLib.txt": "../library/CMakeLists.txt"
        }
    },
    {
        "command": "user/channel -s build_type=Release",
        "folder": "../library",
        "sources":  {
            "../cases/mydetlib_base.cpp": "../library/src/mydetlib.cpp",
            "../cases/CMakeListsLib.txt": "../library/CMakeLists.txt"
        }
    }
]

checks_nothing_debug = [
    {
        "command": "user/channel -s build_type=Debug",
        "folder": "../library",
        "sources":  {
            "../cases/mydetlib_base.cpp": "../library/src/mydetlib.cpp"
        }
    },
    {
        "command": "user/channel -s build_type=Debug",
        "folder": "../library",
        "sources":  {
            "../cases/mydetlib_base.cpp": "../library/src/mydetlib.cpp"
        }
    }
]

checks_nothing_release_2_dirs = [
    {
        "command": "user/channel1 -s build_type=Release",
        "folder": "../library",
        "sources":  {
            "../cases/mydetlib_base.cpp": "../library/src/mydetlib.cpp"
        }
    },
    {
        "command": "user/channel2 -s build_type=Release",
        "folder": "../library",
        "sources":  {
            "../cases/mydetlib_base.cpp": "../library/src/mydetlib.cpp"
        }
    }
]

checks_nothing_debug_2_dirs = [
    {
        "command": "user/channel1 -s build_type=Debug",
        "folder": "../library",
        "sources":  {
            "../cases/mydetlib_base.cpp": "../library/src/mydetlib.cpp"
        }
    },
    {
        "command": "user/channel2 -s build_type=Debug",
        "folder": "../library",
        "sources":  {
            "../cases/mydetlib_base.cpp": "../library/src/mydetlib.cpp"
        }
    }
]

checks_nothing_debug_2_dirs_shared = [
    {
        "command": "user/channel1 -s build_type=Debug -o shared=True",
        "folder": "../library",
        "sources":  {
            "../cases/mydetlib_base.cpp": "../library/src/mydetlib.cpp"
        }
    },
    {
        "command": "user/channel2 -s build_type=Debug -o shared=True",
        "folder": "../library",
        "sources":  {
            "../cases/mydetlib_base.cpp": "../library/src/mydetlib.cpp"
        }
    }
]

checks_date = [
    {
        "command": "user/channel",
        "folder": "../library",
        "sources":  {
            "../cases/mydetlib_macros_date.cpp": "../library/src/mydetlib.cpp"
        }
    },
    {
        "command": "user/channel",
        "folder": "../library",
        "sources":  {
            "../cases/mydetlib_macros_date.cpp": "../library/src/mydetlib.cpp"
        }
    }
]

checks_time = [
    {
        "command": "user/channel",
        "folder": "../library",
        "sources":  {
            "../cases/mydetlib_macros_time.cpp": "../library/src/mydetlib.cpp"
        }
    },
    {
        "command": "user/channel",
        "folder": "../library",
        "sources":  {
            "../cases/mydetlib_macros_time.cpp": "../library/src/mydetlib.cpp"
        }
    }
]

checks_file = [
    {
        "command": "user/channel",
        "folder": "../library",
        "sources":  {
            "../cases/mydetlib_macros_file.cpp": "../library/src/mydetlib.cpp"
        }
    },
    {
        "command": "user/channel",
        "folder": "../library",
        "sources":  {
            "../cases/mydetlib_macros_file.cpp": "../library/src/mydetlib.cpp"
        }
    }
]

checks_file_2_dirs = [
    {
        "command": "user/channel",
        "folder": "../library",
        "sources":  {
            "../cases/mydetlib_macros_file.cpp": "../library/src/mydetlib.cpp"
        }
    },
    {
        "command": "user/channel",
        "folder": "../library",
        "sources":  {
            "../cases/mydetlib_macros_file.cpp": "../library/src/mydetlib.cpp"
        }
    }
]


checks_line = [
    {
        "command": "user/channel",
        "folder": "../library",
        "sources":  {
            "../cases/mydetlib_macros_line.cpp": "../library/src/mydetlib.cpp"
        }
    },
    {
        "command": "user/channel",
        "folder": "../library",
        "sources":  {
            "../cases/mydetlib_macros_line.cpp": "../library/src/mydetlib.cpp"
        }
    }
]

checks_uninitialized_debug = [
    {
        "command": "user/channel -s build_type=Debug",
        "folder": "../library",
        "sources":  {
            "../cases/mydetlib_uninitialized.cpp": "../library/src/mydetlib.cpp"
        }
    },
    {
        "command": "user/channel -s build_type=Debug",
        "folder": "../library",
        "sources":  {
            "../cases/mydetlib_uninitialized.cpp": "../library/src/mydetlib.cpp"
        }
    }
]

checks_uninitialized_release = [
    {
        "command": "user/channel -s build_type=Release",
        "folder": "../library",
        "sources":  {
            "../cases/mydetlib_uninitialized.cpp": "../library/src/mydetlib.cpp"
        }
    },
    {
        "command": "user/channel -s build_type=Release",
        "folder": "../library",
        "sources":  {
            "../cases/mydetlib_uninitialized.cpp": "../library/src/mydetlib.cpp"
        }
    }
]

checks_initialized_debug = [
    {
        "command": "user/channel -s build_type=Debug",
        "folder": "../library",
        "sources":  {
            "../cases/mydetlib_initialized.cpp": "../library/src/mydetlib.cpp"
        }
    },
    {
        "command": "user/channel -s build_type=Debug",
        "folder": "../library",
        "sources":  {
            "../cases/mydetlib_initialized.cpp": "../library/src/mydetlib.cpp"
        }
    }
]

checks_initialized_release = [
    {
        "command": "user/channel -s build_type=Release",
        "folder": "../library",
        "sources":  {
            "../cases/mydetlib_initialized.cpp": "../library/src/mydetlib.cpp"
        }
    },
    {
        "command": "user/channel -s build_type=Release",
        "folder": "../library",
        "sources":  {
            "../cases/mydetlib_initialized.cpp": "../library/src/mydetlib.cpp"
        }
    }
]

checks_lto_flags = [
    {
        "command": "user/channel -s build_type=Release",
        "folder": "../library",
        "sources":  {
            "../cases/mydetlib_base.cpp": "../library/src/mydetlib.cpp",
            "../cases/CMakeListsLibLto.txt": "../library/CMakeLists.txt"
        }
    },
    {
        "command": "user/channel -s build_type=Release",
        "folder": "../library",
        "sources":  {
            "../cases/mydetlib_base.cpp": "../library/src/mydetlib.cpp",
            "../cases/CMakeListsLibLto.txt": "../library/CMakeLists.txt"
        }
    }
]

checks_random_seed_fix_lto_flags = [
    {
        "command": "user/channel -s build_type=Release",
        "folder": "../library",
        "sources":  {
            "../cases/mydetlib_base.cpp": "../library/src/mydetlib.cpp",
            "../cases/CMakeListsFixLibLto.txt": "../library/CMakeLists.txt"
        }
    },
    {
        "command": "user/channel -s build_type=Release",
        "folder": "../library",
        "sources":  {
            "../cases/mydetlib_base.cpp": "../library/src/mydetlib.cpp",
            "../cases/CMakeListsFixLibLto.txt": "../library/CMakeLists.txt"
        }
    }
]


variation_cases = [
    Case("Empty library Release", checks_nothing_release, False),
    Case("Empty library Release", checks_nothing_release, True),
    Case("Empty library Debug", checks_nothing_debug, False),
    Case("Empty library Debug", checks_nothing_debug, True),
    Case("Empty library Release, 2 dirs", checks_nothing_release_2_dirs, False),
    Case("Empty library Debug, 2 dirs", checks_nothing_debug_2_dirs, False),
    Case("Empty library Release, 2 dirs", checks_nothing_release_2_dirs, True),
    Case("Empty library Debug, 2 dirs", checks_nothing_debug_2_dirs, True),
    Case("Empty library Debug, 2 dirs shared",checks_nothing_debug_2_dirs_shared, False),
    #Case("Empty library Debug, 2 dirs shared",checks_nothing_debug_2_dirs_shared, True),
    Case("Library using __DATE__ macro", checks_date, False),
    Case("Library using __TIME__ macro", checks_time, False),
    Case("Library using __FILE__ macro", checks_file, False),
    Case("Library using __FILE__ macro, 2 dirs", checks_file_2_dirs, False),
    #Case("Library using __LINE__ macro", checks_line, False),
    Case("Library using __DATE__ macro", checks_date, True),
    Case("Library using __TIME__ macro", checks_time, True),
    Case("Library using __FILE__ macro", checks_file, True),
    Case("Library using __FILE__ macro, 2 dirs", checks_file_2_dirs, True),
    #Case("Library using __LINE__ macro", checks_line, True),
    #Case("Initialized data Debug", checks_uninitialized_debug, False),
    #Case("Initialized data Release", checks_uninitialized_release, False),
    #Case("Uninitialized data Debug", checks_uninitialized_debug, False),
    #Case("Uninitialized data Release", checks_uninitialized_release, False),
    #Case("Initialized data Debug", checks_uninitialized_debug, True),
    #Case("Initialized data Release", checks_uninitialized_release, True),
    #Case("Uninitialized data Debug", checks_uninitialized_debug, True),
    #Case("Uninitialized data Release", checks_uninitialized_release, True),
]

if "gcc" in compiler:
    variation_cases.extend([
        Case("gcc: Use LTO flags", checks_lto_flags, False),
        Case("gcc: Empty library Fix LTO", checks_random_seed_fix_lto_flags, False),
        Case("gcc: Use LTO flags", checks_lto_flags, True),
        Case("gcc: Empty library Fix LTO", checks_random_seed_fix_lto_flags, True)
    ])

results = {}

for case in variation_cases:
    hook_state, success = case.launch_case()
    if not case.name in results:
        results[case.name] = {True: None, False: None}

    results[case.name][hook_state] = success

print_results(results)
