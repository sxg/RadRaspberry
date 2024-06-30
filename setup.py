from setuptools import setup, find_packages

setup(
    name="rad_raspberry",
    version="1.1.0",
    packages=find_packages(),
    install_requires=[
        "setuptools==69.5.1",
        "asyncio",
        "aiohttp",
    ],
    license="MIT",
    entry_points={
        "console_scripts": ["rad_raspberry=rad_raspberry.main:main"]
    },
    author="Satyam Ghodasara",
    author_email="sghodas@gmail.com",
    description="A tool to take attendance with a Raspberry Pi.",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/sxg/rad_raspberry",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
    ],
)
