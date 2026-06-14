from setuptools import setup, find_packages

with open("requirements.txt") as f:
    install_requires = f.read().strip().split("\n")

setup(
    name="fatura_ai",
    version="1.0.0",
    description="Fatura AI - AI-powered invoice import for ERPNext",
    author="BOT Solutions",
    author_email="support@botsolutions.tech",
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=install_requires,
)
