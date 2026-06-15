from setuptools import setup, find_packages

with open("requirements.txt") as f:
    install_requires = f.read().strip().split("\n")

# Read version from package __init__ — single source of truth
_about = {}
exec(open("fatura_ai/__init__.py").read(), _about)

setup(
    name="fatura_ai",
    version=_about["__version__"],
    description="AI-powered supplier invoice import for ERPNext — Saudi market",
    author="BOT Solutions",
    author_email="info@botsolutions.tech",
    license="MIT",
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=install_requires,
)
