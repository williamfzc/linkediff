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
import pathlib

import pydot
import xmind
from unidiff import PatchSet, PatchedFile, Hunk
from pydantic import BaseModel


class AffectedFunction(dict):
    def get_name(self) -> str:
        return self["Name"]

    def get_package_name(self) -> str:
        return self["Package"]

    def get_full_name(self) -> str:
        return f"{self.get_package_name()}.{self['NodeName']}.{self['Name']}"


class AffectedCall(dict):
    def get_src(self) -> str:
        return self["src"]

    def get_dst(self) -> str:
        return self["dst"]


class _PatchMixin(object):
    def __init__(self):
        self.patch: typing.Optional[PatchSet] = None

    def load_patch_from_name(self, patch_file: str, **kwargs):
        self.patch = PatchSet.from_filename(patch_file, **kwargs)

    def load_patch_from_string(self, patch_str: str, **kwargs):
        self.patch = PatchSet.from_string(patch_str, **kwargs)


class _CocaMixin(object):
    TAG_TYPE = "type"
    TYPE_DIRECT = "direct"
    TYPE_INDIRECT = "indirect"

    TAG_SRC = "src"
    TAG_DST = "dst"
    CHARSET = "utf-8"

    def __init__(self):
        self.coca_cmd = "coca"
        self.coca_workspace = pathlib.Path(".")
        self.coca_deps = None

    @property
    def coca_deps_path(self) -> pathlib.Path:
        return self.coca_workspace / "coca_reporter" / "deps.json"

    @property
    def coca_call_path(self) -> pathlib.Path:
        return self.coca_workspace / "coca_reporter" / "call.dot"

    def exec_coca_analysis(self):
        subprocess.check_call([self.coca_cmd, "analysis"], cwd=self.coca_workspace)

    def exec_coca_call_graph(
        self, function_name: str, package_range: str, direct_only: bool = True
    ) -> typing.List[AffectedCall]:
        if self.coca_call_path.is_file():
            self.coca_call_path.unlink()

        cmd = [self.coca_cmd, "call", "-c", function_name]
        # will not use this filter which causes some path issues
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
            AffectedCall(zip((self.TAG_SRC, self.TAG_DST, self.TAG_TYPE), each))
            for each in ret
        ]

    def dep_existed(self) -> bool:
        return self.coca_deps is not None

    def load_deps(self):
        with self.coca_deps_path.open(encoding=self.CHARSET) as f:
            raw_coca_deps = json.load(f)
        ret = dict()
        for each in raw_coca_deps:
            file_path = each["FilePath"]
            # replace '\'
            file_path = pathlib.Path(file_path).as_posix()

            if file_path not in ret:
                ret[file_path] = []
            ret[file_path].append(each)
        self.coca_deps = ret


class DiffBlock(BaseModel):
    file: str = ""
    start: int = -1
    end: int = -1
    affected_functions: typing.List[AffectedFunction] = []
    affected_calls: typing.List[AffectedCall] = []
    affected_r_calls: typing.List[dict] = []


class Diff(dict):
    def to_json(self) -> str:
        return json.dumps(self, default=lambda o: o.dict())

    def to_json_file(self, file_path: str, **kwargs):
        with open(file_path, "w", **kwargs) as f:
            f.write(self.to_json())

    # todo: dot graph is too huge to read
    # maybe xmind?
    def to_dot_graph(self) -> pydot.Dot:
        graph = pydot.Dot()
        for file_name, blocks in self.items():
            cur_dot = pydot.Node(file_name, label=file_name)
            graph.add_node(cur_dot)

            # blocks
            for each_block in blocks:
                each_block: DiffBlock
                cur_block_dot = pydot.Node(
                    f"{cur_dot.get_name()[1:-1]}-{each_block.start}-{each_block.end}",
                    label=f"{each_block.start}-{each_block.end}",
                )
                graph.add_node(cur_block_dot)
                graph.add_edge(pydot.Edge(cur_dot.get_name(), cur_block_dot.get_name()))

                # affected functions
                for each_affected in each_block.affected_functions:
                    cur_func_dot = pydot.Node(
                        f"{cur_block_dot.get_name()[1:-1]}-{each_affected.get_name()}",
                        label=each_affected.get_name(),
                    )
                    graph.add_node(cur_func_dot)
                    graph.add_edge(
                        pydot.Edge(cur_block_dot.get_name(), cur_func_dot.get_name())
                    )

                    # calls
                    calls_dot = pydot.Node(
                        f"{cur_func_dot.get_name()[1:-1]}-calls", label="calls"
                    )
                    graph.add_node(calls_dot)
                    graph.add_edge(
                        pydot.Edge(cur_func_dot.get_name(), calls_dot.get_name())
                    )

                    for each_call in each_block.affected_calls:
                        call_src = each_call.get_src()
                        call_dst = each_call.get_dst()
                        full_call = each_affected.get_full_name()
                        if call_src != full_call:
                            continue
                        each_call_dot = pydot.Node(
                            f"{calls_dot.get_name()[1:-1]}-{call_dst}", label=call_dst
                        )
                        graph.add_node(each_call_dot)
                        graph.add_edge(
                            pydot.Edge(calls_dot.get_name(), each_call_dot.get_name())
                        )

        return graph

    def to_xmind_file(self, file_path: str):
        workbook = xmind.load(file_path)
        sheet = workbook.getPrimarySheet()
        root = sheet.getRootTopic()
        for file_name, blocks in self.items():
            cur_file_node = root.addSubTopic()
            cur_file_node.setTitle(file_name)

            # blocks
            for each_block in blocks:
                each_block: DiffBlock

                cur_block_node = cur_file_node.addSubTopic()
                cur_block_node.setTitle(f"{each_block.start}-{each_block.end}")

                # affected functions
                for each_affected in each_block.affected_functions:
                    cur_affected_node = cur_block_node.addSubTopic()
                    cur_affected_node.setTitle(each_affected.get_full_name())

                    calls_node = cur_affected_node.addSubTopic()
                    calls_node.setTitle("calls")

                    for each_call in each_block.affected_calls:
                        call_src = each_call.get_src()
                        call_dst = each_call.get_dst()
                        full_call = each_affected.get_full_name()
                        if call_src != full_call:
                            continue
                        cur_call_node = calls_node.addSubTopic()
                        cur_call_node.setTitle(call_dst)

        xmind.save(workbook)


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

    def find_affected_functions(self, diff: Diff = None) -> Diff:
        assert self.verify()

        # deps created from current rev
        if not diff:
            diff_dict = self.find_diff_blocks()
        else:
            diff_dict = diff
        assert diff_dict

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
                            each_diff_block.affected_functions.append(
                                AffectedFunction(**each_function)
                            )
        return diff_dict

    def find_affected_calls(self, diff: Diff = None, package_range: str = None) -> Diff:
        assert self.verify()

        # deps created from current rev
        if not diff:
            diff_dict = self.find_affected_functions()
        else:
            diff_dict = diff
        assert diff_dict

        # mapping
        for file_name, blocks in diff_dict.items():
            for each_block in blocks:
                each_block: DiffBlock
                for each_func in each_block.affected_functions:
                    full_call = each_func.get_full_name()
                    all_calls = self.exec_coca_call_graph(full_call, "")
                    if not package_range:
                        continue
                    each_block.affected_calls = [
                        each
                        for each in all_calls
                        if each.get_dst().startswith(package_range)
                    ]
        return diff_dict
