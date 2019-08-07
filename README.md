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

There are lots of efforts coming from different organizations in the past years to achieve deterministic builds such as [Chromium](https://www.chromium.org/developers/testing/isolated-testing/deterministic-builds), [Reproducible builds](https://reproducible-builds.org/), or [Yocto](https://wiki.yoctoproject.org/wiki/Reproducible_Builds).

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

## Timestamps introduced by the compiler / linker

Because of the use of macros like `__DATE__` or `__TIME__` or because of the definition of the file format (like `PE` in Windows and `Mach-O` in MacOs)

Windows: patch binaries
MacOs: option to set `ZERO_AR_DATE`
Linux: set `SOURCE_DATE_EPOCH`

## Build folder information propagated to binaries

`__FILE__` macro

## Randomness created by the compiler

Like using the `-flto` flag in gcc

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


