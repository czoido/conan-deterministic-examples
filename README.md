## Experiments on how to achieve C++ deterministic builds with Conan [![Build Status](https://travis-ci.org/czoido/conan-deterministic-examples.svg?branch=master)](https://travis-ci.org/czoido/conan-deterministic-examples) [![Build status](https://ci.appveyor.com/api/projects/status/i538q9jia0lsg0sn?svg=true)](https://ci.appveyor.com/project/czoido/conan-deterministic-examples)

**NOTE: this is a work in progress and is highly experimental**

# What are deterministic builds ?

Deterministic builds is the process of building sources at the same revision with the same build environment
and build instructions producing exactly the same binary in two builds, even if they are made on different
machines, build directories and with different names. They are also sometimes called reproducible or hermetic
builds.

Let's note that deterministic builds are not something that happens naturally. Normal projects do not produce
deterministic builds and the reasons that they are not produced can be different for each operating system and
compiler.

Deterministic builds should be guaranteed for a given *build environment*. That means that certain variables
such as the operating system, build system versions, target architecture should remain the same between
different builds.

There are lots of efforts coming from different organizations in the past years to achieve deterministic
builds such as [Chromium](https://www.chromium.org/developers/testing/isolated-testing/deterministic-builds),
[Reproducible builds](https://reproducible-builds.org/), or
[Yocto](https://wiki.yoctoproject.org/wiki/Reproducible_Builds).

# The importance of deterministic builds

There are two main reasons why deterministic builds are important:

 - **Security**. Modifying binaries instead of the upstream source code can make the changes invisible for the
   original authors. This can be fatal in safety critical environments such as medical, aerospace and
   automotive. So promising indentical results for given inputs allows third parties to come to a consensus
   con a *correct* result.

- **Storaging binaries**. If you want to have a repository to store your binaries you do not want to generate
  binaries binaries with random checksums when sources at the same revision. That could lead the system to
  make store different binaries that in fact should be the same.

The second case could be a concern if you are using Conan to manage your packages. For example, if you have
revisions enabled and are working in Windows or MacOs the most simple library will lead to two different
binaries  

# Sources of variation

There are many different reasons for that your builds can end being non-deterministic. Reasons will vary
between different operating systems and compilers. Not all compilers or linkers have the option to introduce
certain flags to fix the sources of indeterminism. In `gcc` and `clang` for example there are some options or
environment variables that can to minimize the indeterminisitic behaviour but using `msvc` you will probably
need to patch the builtbinaries as there are no options available to prevent the propagation of certain
information to the binaries.

This repository contains a python script called `check_deterministic.py` which produces binaries affected by
different causes of indeterminism and tries to fix them two ways:
- Applying a Conan hook. This hook can be used to setup environment variables in the `pre_build` step and
  patch binaries in `post_build`. The intention of the annexed hook named `deterministic-build.py` is to show
  the tools that can be used to produce deterministic builds but not to enter in much detail in how to do it. 
- Modifying compiler/linker flags in the `CMakeLists.txt`.

Here are the most common sources of indeterminism that can happen and possible solutions to avoid them.

## Timestamps introduced by the compiler / linker

There are two main reasons for that our binaries could end up containing time information that will make them
not reproducible:

- The use of `__DATE__` or `__TIME__` macros in the sources.

- When the definition of the file format forces to store time information in the object files. This is the
  case of `Portable Executable` fornmat in Windows and `Mach-O` in MacOs. In Linux `ELF` files do not encode
  any kind of timestamp. 

### Possible solutions

The solutions depend on the compiler used:

- `msvc` can neither set the timestamps for the macros or avoid introducing time information from the `PE`
  format with environment variables or compiler flags. The only way to remove this information from the
  binaries is parsing the file format and replacing the bytes that contain non-deterministic information. That
  can be done in the `post_build` step launching patching tools.

- `gcc` detects the existence of the `SOURCE_DATE_EPOCH` environment variable. If this variable is set, its
  value specifies a UNIX timestamp to be used in replacement of the current date and time in the `__DATE__`
  and `__TIME__` macros, so that the embedded timestamps become reproducible. The value can be set to a known
  timestamp such as the last modification time of the source or package.

- `clang` makes use of `ZERO_AR_DATE` that if set, resets the timestamp that is introduced in the binary
  setting it to epoch 0.

These variables can be set by the Conan hook in the `pre_build` step calling a function like `set_environment`
and the restored if necessary in the `post_build` step with something like `reset_environment`. 

```python
def set_environment(self):
    if self._os == "Linux":
        self._old_source_date_epoch = os.environ.get("SOURCE_DATE_EPOCH")
        timestamp = "1564483496"
        os.environ["SOURCE_DATE_EPOCH"] = timestamp
        self._output.info(
            "set SOURCE_DATE_EPOCH: {}".format(timestamp))
    elif self._os == "Macos":
        os.environ["ZERO_AR_DATE"] = "1"
        self._output.info(
            "set ZERO_AR_DATE: {}".format(timestamp))

def reset_environment(self):
    if self._os == "Linux":
        if self._old_source_date_epoch is None:
            del os.environ["SOURCE_DATE_EPOCH"]
        else:
            os.environ["SOURCE_DATE_EPOCH"] = self._old_source_date_epoch
    elif self._os == "Macos":
        del os.environ["ZERO_AR_DATE"]
```

## Build folder information propagated to binaries

If the same sources are compiled in different folders sometimes folder information is propagated to the
binaries. This can happen mainly for two reasons:

- Use of macros that contain current file information like `__FILE__` macro.
- Creating debug binaries that store information of where the sources are.

### Possible solutions

Again the solutions will depend on the compiler used:

- `msvc` can't set options to avoid the propagation of this information to the binary files. The only way to
  get reproducible binaries is again using a Hook to strip this information in the build step. Note that as we
  are patching the binaries to achieve reproducible binaries folders of the same length in characters should
  be used for each build.  

- `gcc` has three compiler flags to work around the issue:
    - `-fdebug-prefix-map=OLD=NEW` can strip directory prefixes from debug info.
    - `-fmacro-prefix-map=OLD=NEW` is available since `gcc 8` and addresses irreproducibility due to the use
      of `__FILE__` macro.
    - `-ffile-prefix-map=OLD=NEW` is available sice `gcc 8` and is the union of `-fdebug-prefix-map` and
      `-fmacro-prefix-map`

- `clang` supports `-fdebug-prefix-map=OLD=NEW` from version 3.8 and is working on supporting the other two
  flags for future versions.

The best way to solve this is adding the flags to compiler options, for example is using `CMake`:

```
add_definitions("-ffile-prefix-map=${CMAKE_SOURCE_DIR}=.")
```

## Randomness created by the compiler

This problem arises for example in `gcc` when Link-Time Optimizations are activated (with the `-flto` flag).
This options introduces random generated names in the binary files. The only way to avoid this problem is to
use `-frandom-seed` flag. This option provides a seed that `gcc` uses when it would otherwise use random
numbers. It is used to generate certain symbol names that have to be different in every compiled file.  It is
also used to place unique stamps in coverage data files and the object files that produce them. This setting
has to be different for each source file. One option would be to set it to the checksum of the file so the
probabilty of colission is very low. For example in CMake it would be like this:

```
set(LIB_SOURCES
    ./src/source1.cpp
    ./src/source2.cpp
    ./src/source3.cpp)

foreach(_file ${LIB_SOURCES})
    file(SHA1 ${_file} checksum)
    string(SUBSTRING ${checksum} 0 8 checksum)
    set_property(SOURCE ${_file} APPEND_STRING PROPERTY COMPILE_FLAGS "-frandom-seed=0x${checksum}")
endforeach()
```

## File order feeding to the build system

## Value initialization

...

### References

- https://www.chromium.org/developers/testing/isolated-testing/deterministic-builds
- https://reproducible-builds.org/
- https://wiki.yoctoproject.org/wiki/Reproducible_Builds
- https://stackoverflow.com/questions/1180852/deterministic-builds-under-windows
- https://docs.microsoft.com/en-us/windows/win32/debug/pe-format#archive-library-file-format
- https://devblogs.microsoft.com/oldnewthing/20180103-00/?p=97705

### Tools

- https://diffoscope.org/
- https://salsa.debian.org/reproducible-builds/strip-nondeterminism
- https://github.com/erocarrera/pefile
- https://github.com/trailofbits/pe-parse
- https://github.com/smarttechnologies/peparser
- https://github.com/google/syzygy
- https://github.com/llvm-mirror/llvm/tree/master/tools
- https://github.com/nh2/ar-timestamp-wiper
- https://docs.microsoft.com/en-us/windows-server/administration/windows-commands/fc
- https://try.diffoscope.org/
