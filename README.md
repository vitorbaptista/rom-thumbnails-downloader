# ROM Thumbnails Downloader

**Automatically download box art images for your ROM collection**

This tool scans your ROM directories and generates download commands for matching box art images from the [libretro-thumbnails](https://github.com/libretro-thumbnails/libretro-thumbnails) project. Perfect for retro gaming enthusiasts who want to organize their collections with beautiful box art thumbnails.

## What It Does

- **Scans** your ROM collection directories (Genesis, SNES, NES, etc.)
- **Finds** matching box art images from the libretro-thumbnails database
- **Generates** wget commands to download the images
- **Names** images to match your ROM files perfectly
- **Prefers** USA region box art, with fallbacks to Europe, World, then others
- **Fast** and lightweight - only downloads what you need

## Quick Start

The easiest way to use this tool is with [uvx](https://docs.astral.sh/uv/):

```bash
# Try it on your ROM collection
uvx rom-thumbnails-downloader /path/to/your/roms
```

That's it! The tool will scan your ROMs and show you the wget commands to download matching box art.

## Installation

### Option 1: Use uvx (Recommended)

No installation needed! Just run:

```bash
uvx rom-thumbnails-downloader /path/to/roms
```

### Option 2: Install with pip

```bash
pip install rom-thumbnails-downloader
rom-thumbnails-downloader /path/to/roms
```

## Usage Examples

### Basic Usage

```bash
# Scan your ROM collection and see what images are available
uvx rom-thumbnails-downloader ~/roms

# The tool will output wget commands like this:
# wget "https://raw.githubusercontent.com/libretro-thumbnails/Sega_-_Mega_Drive_-_Genesis/refs/heads/master/Named_Boxarts/Sonic%20the%20Hedgehog%20(USA).png" -O "/home/user/roms/genesis/Sonic the Hedgehog (USA).png"
```

### Download the Images

The tool generates wget commands but doesn't download automatically. To actually download the images:

```bash
# Generate and execute the download commands
uvx rom-thumbnails-downloader ~/roms | bash
```

### Save Commands to a File

```bash
# Save download commands to review first
uvx rom-thumbnails-downloader ~/roms > download_images.sh
chmod +x download_images.sh
./download_images.sh
```

## Expected Directory Structure

Your ROM collection should be organized like this:

```
roms/
├── genesis/
│   ├── Sonic the Hedgehog (USA).bin
│   ├── Streets of Rage (USA).bin
│   └── ...
├── snes/
│   ├── Super Mario World (USA).sfc
│   ├── The Legend of Zelda - A Link to the Past (USA).sfc
│   └── ...
├── nes/
│   ├── Super Mario Bros. (USA).nes
│   ├── The Legend of Zelda (USA).nes
│   └── ...
└── ...
```

After running the tool and downloading images:

```
roms/
├── genesis/
│   ├── Sonic the Hedgehog (USA).bin
│   ├── Sonic the Hedgehog (USA).png     ← Downloaded box art
│   ├── Streets of Rage (USA).bin
│   ├── Streets of Rage (USA).png        ← Downloaded box art
│   └── ...
└── ...
```

## Supported Systems

This tool supports all gaming systems available in the [libretro-thumbnails repository](https://github.com/libretro-thumbnails/libretro-thumbnails), including:

- All major consoles (Nintendo, Sega, Sony, Microsoft, Atari, etc.)
- Handheld systems (Game Boy, Game Gear, PSP, etc.)
- Arcade systems (MAME, FBNeo, etc.)
- Computer systems (Amiga, DOS, MSX, etc.)
- And many more!

The tool automatically maps common ROM folder names (like `genesis`, `snes`, `nes`) to the correct libretro-thumbnails system names.

## How It Works

1. **Scan**: The tool scans your ROM directories and catalogs all ROM files
2. **Clean**: ROM filenames are cleaned (removing regions, revisions, file extensions)
3. **Match**: Cleaned names are matched against the libretro-thumbnails database
4. **Prioritize**: USA region box art is preferred, with smart fallbacks
5. **Generate**: wget commands are created for downloading matching images
6. **Skip**: Already existing image files are automatically skipped

## Troubleshooting

### No images found for my ROMs

- **Check system folder names**: Make sure your ROM folders use standard names like `genesis`, `snes`, `nes`, etc.
- **Verify ROM filenames**: ROMs should have recognizable game titles. Files like `game1.bin` won't match anything.
- **Check the database**: Not every ROM has box art available in libretro-thumbnails.

### Images download to wrong location

- The tool places images next to your ROM files with the same name but `.png` extension
- Make sure you have write permissions to your ROM directories

### Tool says "Console not found in CSV data"

- This means the system isn't in our database yet, but it might be in libretro-thumbnails
- The tool will still try to match ROMs but won't find images to download

### Some ROMs get skipped

- ROMs with very generic names or heavily modified filenames might not match
- The tool automatically skips ROMs that already have associated PNG files

## Region Preferences

The tool uses smart region preference:

1. **USA** versions (preferred)
2. **Europe** versions
3. **World** versions
4. **Other regions** (Japan, etc.)

This means if a game has both "Super Mario World (USA)" and "Super Mario World (Europe)" box art available, it will choose the USA version.

## What's Included

- Box art images from the libretro-thumbnails project
- Smart ROM filename cleaning and matching
- Automatic region preference handling
- Support for 90+ gaming systems
- Safe operation (won't overwrite existing images)

## Support

Having issues? Check the [libretro-thumbnails repository](https://github.com/libretro-thumbnails/libretro-thumbnails) to see if box art exists for your games, or open an issue in this project's repository.

## License

MIT License - feel free to use this tool for organizing your personal ROM collections.
