import fire
from pydantic import BaseModel
import pathlib

from smartdiff import SmartDiff

CONFIG_FILE_NAME = ".smartdiff.json"


class SmartDiffConfig(BaseModel):
    coca_cmd: str = "coca"
    patch_file: str = ""

    package_range: str = ""
    to_json: str = ""
    to_xmind: str = ""

    @staticmethod
    def init_from_project() -> "SmartDiffConfig":
        config = pathlib.Path(CONFIG_FILE_NAME)
        if not config.is_file():
            raise FileNotFoundError(f"no config file found: {config.absolute()}")
        return SmartDiffConfig.parse_file(CONFIG_FILE_NAME)


class SmartDiffCli(object):
    def run(self):
        conf = SmartDiffConfig.init_from_project()
        patch_file = pathlib.Path(conf.patch_file)
        if not patch_file.is_file():
            raise FileNotFoundError(f"no patch file found: {patch_file.absolute()}")

        sd = SmartDiff()
        sd.coca_cmd = conf.coca_cmd
        sd.load_patch_from_name(conf.patch_file)
        sd.exec_coca_analysis()
        sd.load_deps()

        result = sd.find_affected_calls(package_range=conf.package_range)
        result = sd.find_affected_r_calls(result, package_range=conf.package_range)

        if conf.to_json:
            result.to_json_file(conf.to_json)
        if conf.to_xmind:
            result.to_xmind_file(conf.to_xmind)

    def init(self, **kwargs):
        conf = SmartDiffConfig(**kwargs)
        with open(CONFIG_FILE_NAME, "w") as f:
            f.write(conf.json())


def main():
    fire.Fire(SmartDiffCli)


if __name__ == "__main__":
    main()
