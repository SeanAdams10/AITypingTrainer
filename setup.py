from setuptools import find_packages, setup

setup(
    name="aitypingtrainer",
    version="0.1.0",
    packages=find_packages(include=['models*', 'tests*']),
    install_requires=[
        # List your project's dependencies here
    ],
)
