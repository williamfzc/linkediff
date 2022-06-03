# MIT License
#
# Copyright (c) 2022 williamfzc
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from unidiff import PatchSet, PatchedFile, Hunk
import typing
import subprocess
import os
import json


class _PatchMixin(object):
    def __init__(self):
        self.patch: typing.Optional[PatchSet] = None

    def load_patch_from_name(self, patch_file: str):
        self.patch = PatchSet.from_filename(patch_file)

    def load_patch_from_string(self, patch_str: str):
        self.patch = PatchSet.from_string(patch_str)


class _CocaMixin(object):
    def __init__(self):
        self.coca_cmd = "coca"
        self.coca_deps_path = "./coca_reporter/deps.json"
        self.coca_deps = None

    def exec_coca_analysis(self):
        subprocess.check_call([self.coca_cmd, "analysis"])

    def dep_existed(self) -> bool:
        return self.coca_deps is not None

    def load_deps(self):
        with open(self.coca_deps_path) as f:
            raw_coca_deps = json.load(f)
        ret = dict()
        for each in raw_coca_deps:
            file_path = each["FilePath"]
            if file_path not in ret:
                ret[file_path] = []
            ret[file_path].append(each)
        self.coca_deps = ret


class DiffBlock(object):
    def __init__(self):
        self.file = ""
        self.start: int = -1
        self.end: int = -1
        self.affected_functions = []


class SmartDiff(_PatchMixin, _CocaMixin):
    def __init__(self):
        super(_PatchMixin, self).__init__()
        super(_CocaMixin, self).__init__()

    def verify(self) -> bool:
        return (self.patch is not None) and (self.coca_deps is not None)

    def find_diff_blocks(self) -> dict:
        diff_dict = dict()
        for each_patched_file in (*self.patch.modified_files, *self.patch.added_files):
            each_patched_file: PatchedFile

            # file name starts with `b/`
            diff_block_list = []
            target_file = each_patched_file.target_file[2:]

            for each_block in each_patched_file:
                # each block in file
                each_block: Hunk

                diff_block = DiffBlock()
                diff_block.file = target_file
                diff_block.start = each_block.target_start
                diff_block.end = each_block.target_start + each_block.target_length
                diff_block_list.append(diff_block)

            diff_dict[target_file] = diff_block_list
        return diff_dict

    def find_diff_methods(self) -> dict:
        assert self.verify()

        # deps created from current rev
        diff_dict = self.find_diff_blocks()

        # mapping
        for file_name, blocks in diff_dict.items():
            if file_name not in self.coca_deps:
                print(f"file {file_name} not in deps")
                continue

            cur_nodes = self.coca_deps[file_name]
            for each_node in cur_nodes:
                functions = each_node["Functions"]
                if not functions:
                    continue

                for each_diff_block in blocks:
                    block_start = each_diff_block.start
                    block_stop = each_diff_block.end
                    for each_function in functions:
                        if not each_function["Name"]:
                            continue
                        function_pos = each_function["Position"]
                        if (
                            block_stop >= function_pos["StartLine"]
                            or block_start <= function_pos["StopLine"]
                        ):
                            each_diff_block.affected_functions.append(each_function)
        return diff_dict
