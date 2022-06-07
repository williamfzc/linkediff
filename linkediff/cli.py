import fire
from pydantic import BaseModel
import pathlib

from linkediff import Linkediff

CONFIG_FILE_NAME = ".linkediff.json"


class LinkediffConfig(BaseModel):
    coca_cmd: str = "coca"
    patch_cmd: str = "git diff HEAD~1 HEAD"
    patch_file: str = ""

    package_range: str = ""
    to_json: str = "ldresult.json"
    to_xmind: str = "ldresult.xmind"

    @staticmethod
    def init_from_project() -> "LinkediffConfig":
        return LinkediffConfig.parse_file(CONFIG_FILE_NAME)

    @staticmethod
    def config_file_existed() -> bool:
        return pathlib.Path(CONFIG_FILE_NAME).is_file()


class LinkediffCli(object):
    def run(self, **kwargs):
        if not LinkediffConfig.config_file_existed():
            self.init(**kwargs)
        conf = LinkediffConfig.init_from_project()
        sd = Linkediff()
        sd.coca_cmd = conf.coca_cmd

        patch_file = pathlib.Path(conf.patch_file)
        if patch_file.is_file():
            sd.load_patch_from_name(conf.patch_file)
        else:
            sd.load_patch_from_cmd(conf.patch_cmd)

        sd.exec_coca_analysis()
        sd.load_deps()

        result = sd.find_affected_calls(package_range=conf.package_range)
        result = sd.find_affected_r_calls(result, package_range=conf.package_range)

        if conf.to_json:
            result.to_json_file(conf.to_json)
        if conf.to_xmind:
            result.to_xmind_file(conf.to_xmind)

    def init(self, **kwargs):
        conf = LinkediffConfig(**kwargs)

        with open(CONFIG_FILE_NAME, "w") as f:
            f.write(conf.json(indent=4))


def main():
    fire.Fire(LinkediffCli)


if __name__ == "__main__":
    main()
