from setuptools import setup, find_packages

setup(
    name="energy-analysis",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        'requests>=2.25.1',
        'pytest>=6.2.4',
    ],
)