from setuptools import setup, find_packages

setup(
    name="mcp_salesforce",
    version="0.1.0",
    packages=find_packages(),
    package_data={
        "mcp_salesforce": ["resources/*"]
    },
    include_package_data=True,
    install_requires=[
        "simple-salesforce>=1.12.5",
        "keyring>=24.3.0"
    ],
    python_requires=">=3.9",
)