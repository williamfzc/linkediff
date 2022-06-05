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

import json
import subprocess
import typing
import os

import pydot
from unidiff import PatchSet, PatchedFile, Hunk
from pydantic import BaseModel


class _PatchMixin(object):
    def __init__(self):
        self.patch: typing.Optional[PatchSet] = None

    def load_patch_from_name(self, patch_file: str):
        self.patch = PatchSet.from_filename(patch_file)

    def load_patch_from_string(self, patch_str: str):
        self.patch = PatchSet.from_string(patch_str)


class _CocaMixin(object):
    TAG_TYPE = "type"
    TYPE_DIRECT = "direct"
    TYPE_INDIRECT = "indirect"

    TAG_SRC = "src"
    TAG_DST = "dst"

    def __init__(self):
        self.coca_cmd = "coca"
        self.coca_deps_path = "./coca_reporter/deps.json"
        self.coca_call_path = "./coca_reporter/call.dot"
        self.coca_deps = None

    def exec_coca_analysis(self):
        subprocess.check_call([self.coca_cmd, "analysis"])

    def exec_coca_call_graph(
        self, function_name: str, package_range: str, direct_only: bool = True
    ) -> typing.List[typing.Dict]:
        if os.path.isfile(self.coca_call_path):
            os.remove(self.coca_call_path)

        cmd = [self.coca_cmd, "call", "-c", function_name]
        if package_range:
            cmd += ["-r", f"{package_range}."]
        subprocess.check_call(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        graphs = pydot.graph_from_dot_file(self.coca_call_path)
        # only one graph
        graph = graphs[0]
        ret = set()

        for each_edge in graph.get_edge_list():
            cur = (
                # remove extra `"`
                each_edge.get_source()[1:-1],
                each_edge.get_destination()[1:-1],
                self.TYPE_DIRECT
                if function_name in each_edge.get_source()
                else self.TYPE_INDIRECT,
            )
            if direct_only and cur[2] == self.TYPE_DIRECT:
                ret.add(cur)

        return [
            dict(zip((self.TAG_SRC, self.TAG_DST, self.TAG_TYPE), each)) for each in ret
        ]

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


class DiffBlock(BaseModel):
    file = ""
    start: int = -1
    end: int = -1
    affected_functions: typing.List[dict] = []
    affected_calls: typing.List[dict] = []
    affected_r_calls: typing.List[dict] = []


class Diff(dict):
    def to_json(self) -> str:
        return json.dumps(self, default=lambda o: o.dict())

    def to_json_file(self, file_path: str, **kwargs):
        with open(file_path, "w", **kwargs) as f:
            f.write(self.to_json())


class SmartDiff(_PatchMixin, _CocaMixin):
    def __init__(self):
        super(_PatchMixin, self).__init__()
        super(_CocaMixin, self).__init__()

    def verify(self) -> bool:
        return (self.patch is not None) and (self.coca_deps is not None)

    def find_diff_blocks(self) -> Diff:
        diff_dict = Diff()
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

    def find_diff_methods(self) -> Diff:
        assert self.verify()

        # deps created from current rev
        diff_dict = self.find_diff_blocks()

        # mapping
        for file_name, blocks in diff_dict.items():
            if file_name not in self.coca_deps:
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
                        function_start = int(function_pos["StartLine"])
                        function_stop = int(function_pos["StopLine"])
                        # match?
                        if max(function_start, block_start) < min(
                            function_stop, block_stop
                        ):
                            # `Type` is always `Class`
                            each_function["NodeName"] = each_node["NodeName"]
                            each_function["Package"] = each_node["Package"]
                            each_diff_block.affected_functions.append(each_function)
        return diff_dict
