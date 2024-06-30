from setuptools import setup, find_packages

setup(
    name="rad_raspberry",
    version="1.0.15",
    packages=find_packages(),
    install_requires=[
        "pandas==2.0.3",
        "timedinput==0.1.1",
        "openpyxl==3.1.2",
        "supabase==2.4.5",
        "setuptools==69.5.1",
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
