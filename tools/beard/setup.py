import os

from setuptools import setup, find_packages

setup(
    name="beard",
    version=os.environ.get("BEARD_VERSION", "1.0.9999"),
    packages=find_packages(),
    package_data={"": ["*.in"]},
    license="Internal",
    long_description="Internal",
    install_requires=[
        "click", "requests", "colorama", "appdirs"
    ],
    entry_points="""
[console_scripts]
beard=beard.beard:cli
""",
)
