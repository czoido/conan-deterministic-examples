#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

import os
import hashlib
import re
import struct
from conans.util.files import md5sum


class LibPatcher(object):
    def __init__(self, output, conanfile):
        self._output = output
        self._conanfile = conanfile
        self._os = self._conanfile.settings.get_safe(
            'os') or self._conanfile.settings.get_safe('os_build')
        self._compiler = self._conanfile.settings.get_safe('compiler')
        self._output.info('Conan binary patcher plug-in for Windows')

    def patch(self):
        if self._os == "Windows":
            if self._compiler == "Visual Studio":
                for root, _, filenames in os.walk(self._conanfile.build_folder):
                    for filename in filenames:
                        filename = os.path.join(root, filename)
                        if ".lib" in filename and not self._conanfile.options.shared:
                            self._patch_lib(filename)
                        if ".exe" in filename or ".dll" in filename:
                            self._patch_pe(filename)

    def _patch_lib(self, filename):
        pos = 0
        with open(filename, 'r+b') as f:
            header_start = 8
            timestamp_offset = 16
            timestamp_size = 12
            pos = header_start + timestamp_offset
            f.seek(header_start + timestamp_offset)
            bytes = f.read(timestamp_size)
            pos = pos + timestamp_size
            pattern = bytes
            regex = re.compile(pattern)
            f.seek(0)
            data = f.read()
            for match_obj in regex.finditer(data):
                offset = match_obj.start()
                f.seek(offset)
                f.write(b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00")
                self._output.info(
                    "patching timestamp at pos: {}".format(offset))

            timestamp_str = bytes.decode("utf-8")
            timestamp_int = int(timestamp_str)
            timestamp_bytes = struct.pack("<I", timestamp_int)
            regex = re.compile(timestamp_bytes)
            f.seek(0)
            data = f.read()
            for match_obj in regex.finditer(data):
                offset = match_obj.start()
                f.seek(offset)
                f.write(b"\x00\x00\x00\x00")
                self._output.info(
                    "patching timestamp at pos: {}".format(offset))

    def _patch_pe(self, filename):
        patch_tool_location = "C:/ducible/ducible.exe"
        if os.path.isfile(patch_tool_location):
            self._output.info("patching {}".format(filename))
            self._conanfile.run("{} {}".format(patch_tool_location, filename))
            self._output.info("md5sum: {}".format(md5sum(filename)))


def post_build(output, conanfile, **kwargs):
    print("deterministic builds hook")
    lib_patcher = LibPatcher(output, conanfile)
    lib_patcher.patch()
