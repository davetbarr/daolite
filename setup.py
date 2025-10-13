"""Setup configuration for daolite package."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="daolite",
    version="0.1.0",
    author="David Barr",
    author_email="dave@davetbarr.com",
    description="A Python package for estimating latency in Adaptive Optics Real-time Control Systems",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/davetbarr/daolite",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Astronomy",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    test_suite="tests",
    entry_points={
        'console_scripts': [
            'daolite-pipeline-designer=daolite.gui.pipeline_designer:main',
            'daolite-json-runner=daolite.pipeline.json_runner:main',
            'daolite-centroid-agenda=daolite.gui.centroid_agenda_tool:main',
        ],
    },
)