from setuptools import setup, find_packages

setup(
    name="povichain",
    version="0.1.0",
    description="PoVIChain: Proof-of-Verified-Interaction Chain",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "pyyaml>=6.0",
    ],
)
