# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ROM Thumbnails Downloader is a CLI tool that automatically downloads thumbnail images for ROM collections from the libretro-thumbnails project. It scans ROM directories, matches games with available thumbnails, and generates wget commands for downloading box art, title screens, or gameplay snapshots.

The project uses uv for Python dependency management and follows a data-driven approach with pre-processed CSV files containing image URLs from the libretro-thumbnails repository.

## Commands

### Development
- `make install` - Install dependencies and pre-commit hooks using uv
- `make test` - Run pytest test suite
- `make lint` - Run pre-commit linting checks on all files
- `make data` - Regenerate CSV data from libretro-thumbnails API

### Running the Tool
- `uv run python -m rom_thumbnails_downloader /path/to/roms` - Basic usage
- `uvx rom-thumbnails-downloader /path/to/roms` - Run without installation
- `uv run python -m rom_thumbnails_downloader /path/to/roms --thumbnail-order boxart` - Specify image type
- `uv run python -m rom_thumbnails_downloader /path/to/roms --region-priority japan,usa,europe` - Custom region priority

## Architecture

### Core Components
- **CLI module** (`src/rom_thumbnails_downloader/cli.py`): Main entry point containing all core logic
- **Data processing**: Pre-built CSV files in `data/processed/consoles/` with image URLs for each console
- **Console mapping**: CONSOLE_MAPPING dict maps common ROM folder names to official libretro-thumbnails system names

### Key Functions
- `clean_title()`: Removes file extensions and parenthetical info from ROM filenames for matching
- `discover_roms()`: Scans ROM directories and maps console names using CONSOLE_MAPPING
- `load_csv_data()`: Loads pre-processed thumbnail data with customizable type/region preferences
- `apply_region_preference()`: Selects best image URL based on region priority (default: USA > Europe > World)
- `generate_wget_commands()`: Creates download commands, skipping existing files

### Data Flow
1. Scan ROM directories → clean filenames → map console names
2. Load CSV data → apply thumbnail type priority → apply region preferences
3. Match ROMs with images → generate wget commands → output to stdout

### Configuration
- **Thumbnail types**: snapshot (gameplay), boxart (covers), title_screen (intro screens)
- **Default order**: snapshot → boxart → title_screen
- **Region priority**: Configurable via `--region-priority`, defaults to usa,europe,world
- **Console mapping**: Extensive dict mapping common folder names to libretro system names

## Testing

- Comprehensive unit tests in `tests/test_cli.py` covering all core functions
- Integration tests using fixture ROMs in `tests/fixtures/roms/`
- Tests verify CSV loading, ROM discovery, region preferences, and command generation
- CI runs tests on Python 3.10-3.13 via GitHub Actions

## Data Management

CSV files are pre-generated from libretro-thumbnails API to avoid runtime API calls. The `make data` command regenerates these files by:
1. Fetching console list from GitHub API
2. Getting file trees for each console repository
3. Extracting image URLs and organizing by type (Named_Boxarts, Named_Snaps, Named_Titles)
