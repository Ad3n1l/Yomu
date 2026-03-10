from setuptools import setup, find_packages

setup(
    name="yomu",
    version="1.0.0",
    description="読む — CLI anime downloader for anikai.to and AnimePahe",
    author="Kopret",
    author_email="devkopret@gmail.com",
    url="https://github.com/ad3n1l/yomu",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "requests>=2.28",
        "beautifulsoup4>=4.11",
        "lxml>=4.9",
        "yt-dlp",
    ],
    entry_points={
        "console_scripts": [
            "yomu=yomu.cli:main",
        ],
    },
    classifiers=[
        "Environment :: Console",
        "Topic :: Multimedia :: Video",
    ],
)
