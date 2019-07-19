#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

import os
import hashlib
import re
import struct


class LibPatcher(object):
    def __init__(self, output, conanfile):
        self._output = output
        self._conanfile = conanfile
        self._output.info('conan binary patcher plug-in')

    def patch(self):
        for root, _, filenames in os.walk(self._conanfile.build_folder):
            for filename in filenames:
                filename = os.path.join(root, filename)
                if ".lib" in filename:
                    self._patch_file(filename)

    def _patch_file(self, filename):
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
                f.write(b"\x99\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x99")
                self._output.info(
                    "patching timestamp at pos: {}".format(offset))

            timestamp_str = bytes.decode("utf-8")
            timestamp_int = int(timestamp_str)
            timestamp_bytes = struct.pack("<l", timestamp_int)
            regex = re.compile(timestamp_bytes)
            f.seek(0)
            data = f.read()
            for match_obj in regex.finditer(data):
                offset = match_obj.start()
                f.seek(offset)
                f.write(b"\x99\x00\x00\x99")
                self._output.info(
                    "patching timestamp at pos: {}".format(offset))


def post_build(output, conanfile, **kwargs):
    lib_patcher = LibPatcher(output, conanfile)
    lib_patcher.patch()
