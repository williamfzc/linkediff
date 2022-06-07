from setuptools import setup, find_packages

__PROJECT_NAME__ = r"linkediff"
__AUTHOR__ = r"williamfzc"
__AUTHOR_EMAIL__ = r"fengzc@vip.qq.com"
__LICENSE__ = r"MIT"
__URL__ = r"https://github.com/williamfzc/linkediff"
__VERSION__ = r"0.1.0"
__DESCRIPTION__ = r"diff analysis"


setup(
    name=__PROJECT_NAME__,
    version=__VERSION__,
    description=__DESCRIPTION__,
    author=__AUTHOR__,
    author_email=__AUTHOR_EMAIL__,
    url=__URL__,
    packages=find_packages(),
    include_package_data=True,
    license=__LICENSE__,
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
    ],
    python_requires=">=3.6",
    install_requires=[
        "unidiff",
        "pydot",
        "pydantic",
        "xmind",
        "fire",
    ],
    entry_points={"console_scripts": ["linkediff = linkediff.cli:main"]},
)
