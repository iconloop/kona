from pathlib import Path

from setuptools import setup, find_packages

req_tests = ["pytest"]
req_lint = ["flake8", "flake8-docstrings"]
req_dev = req_tests + req_lint

with open('requirements.txt', 'r') as f:
    requires = [
        s for s in [
            line.split('#', 1)[0].strip(' \t\n') for line in f
        ] if s != ''
    ]

this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

setup_options = {
    "name": "kona",
    "version": "0.1.2",
    "url": "https://github.com/iconloop/kona",
    "author": "ICONLOOP",
    "author_email": "t_core@iconloop.com",
    "description": "Convenience of key value store",
    "long_description": long_description,
    "long_description_content_type": "text/markdown",
    "packages": find_packages(),
    "python_requires": ">=3.9.0",
    "install_requires": requires,
    "extras_require": {
        "tests": req_tests,
        "lint": req_lint,
        "dev": req_dev
    },
    "package_dir": {"": "."},
    "entry_points": {
        "console_scripts": [
            "benchmark=benchmark:main"
        ]
    }
}

setup(**setup_options)
