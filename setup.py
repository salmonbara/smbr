from setuptools import setup, find_packages

setup(
    name="smbr",
    version="1.0.0",
    author="salmonbara",
    description="Recon & Exploitation Tools",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "typer",
        "rich",
        "pyperclip"
    ],
    entry_points={
        "console_scripts": [
            "smbr=smbr.cli:app",
        ],
    },
    python_requires=">=3.8",
)