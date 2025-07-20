"""ROM Thumbnails Downloader - A CLI tool for downloading box art images for ROM files."""

__version__ = "0.1.0"
__author__ = "ROM Thumbnails Downloader"
__description__ = "CLI tool for downloading box art images for ROM files based on libretro-thumbnails data"

from .cli import main

__all__ = ["main"]