from setuptools import setup, find_packages

setup(
    name="aitypingtrainer",
    version="0.1.0",
    packages=find_packages(include=['models*', 'tests*']),
    install_requires=[
        # List your project's dependencies here
    ],
)
