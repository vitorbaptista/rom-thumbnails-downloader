#!/usr/bin/env python3
"""
Match Screenshots CLI script for ROM thumbnail downloading.
Matches ROM files with corresponding box-art images from CSV data.
"""

import argparse
import csv
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Generator
from collections import defaultdict
from urllib.parse import urlparse, quote
import sys
from tqdm import tqdm


# Mapping from user-friendly thumbnail type names to CSV column names
THUMBNAIL_TYPE_MAPPING = {
    "snapshot": "Named_Snaps",
    "boxart": "Named_Boxarts",
    "title_screen": "Named_Titles",
}

# Default thumbnail priority order
DEFAULT_THUMBNAIL_ORDER = ["snapshot", "boxart", "title_screen"]

# Default region priority order
DEFAULT_REGION_ORDER = ["usa", "europe", "world"]

# Mapping from ROM folder system names to CSV console names
CONSOLE_MAPPING = {
    "3do": "The_3DO_Company_-_3DO",
    "amiga": "Commodore_-_Amiga",
    "amiga1200": "Commodore_-_Amiga",
    "amiga600": "Commodore_-_Amiga",
    "amigacd32": "Commodore_-_CD32",
    "amstradcpc": "Amstrad_-_CPC",
    "arcade": "MAME",
    "arcadia": "Emerson_-_Arcadia_2001",
    "arduboy": "Arduboy_Inc_-_Arduboy",
    "atari2600": "Atari_-_2600",
    "atari5200": "Atari_-_5200",
    "atari7800": "Atari_-_7800",
    "atari800": "Atari_-_8-bit",
    "atarijaguar": "Atari_-_Jaguar",
    "atarilynx": "Atari_-_Lynx",
    "atarist": "Atari_-_ST",
    "atarixe": "Atari_-_8-bit",
    "atomiswave": "Atomiswave",
    "c64": "Commodore_-_64",
    "cdtv": "Commodore_-_CDTV",
    "channelf": "Fairchild_-_Channel_F",
    "colecovision": "Coleco_-_ColecoVision",
    "cps": "FBNeo_-_Arcade_Games",
    "cps1": "FBNeo_-_Arcade_Games",
    "cps2": "FBNeo_-_Arcade_Games",
    "cps3": "FBNeo_-_Arcade_Games",
    "dreamcast": "Sega_-_Dreamcast",
    "famicom": "Nintendo_-_Nintendo_Entertainment_System",
    "fba": "FBNeo_-_Arcade_Games",
    "fbneo": "FBNeo_-_Arcade_Games",
    "fds": "Nintendo_-_Family_Computer_Disk_System",
    "gamegear": "Sega_-_Game_Gear",
    "gb": "Nintendo_-_Game_Boy",
    "gba": "Nintendo_-_Game_Boy_Advance",
    "gbc": "Nintendo_-_Game_Boy_Color",
    "gc": "Nintendo_-_GameCube",
    "genesis": "Sega_-_Mega_Drive_-_Genesis",
    "gx4000": "Amstrad_-_GX4000",
    "intellivision": "Mattel_-_Intellivision",
    "mame": "MAME",
    "mark3": "Sega_-_Master_System_-_Mark_III",
    "mastersystem": "Sega_-_Master_System_-_Mark_III",
    "megacd": "Sega_-_Mega-CD_-_Sega_CD",
    "megacdjp": "Sega_-_Mega-CD_-_Sega_CD",
    "megadrive": "Sega_-_Mega_Drive_-_Genesis",
    "megadrivejp": "Sega_-_Mega_Drive_-_Genesis",
    "msx": "Microsoft_-_MSX",
    "msx1": "Microsoft_-_MSX",
    "msx2": "Microsoft_-_MSX2",
    "n3ds": "Nintendo_-_Nintendo_3DS",
    "n64": "Nintendo_-_Nintendo_64",
    "n64dd": "Nintendo_-_Nintendo_64DD",
    "naomi": "Sega_-_Naomi",
    "naomi2": "Sega_-_Naomi_2",
    "naomigd": "Sega_-_Naomi",
    "nds": "Nintendo_-_Nintendo_DS",
    "neogeo": "SNK_-_Neo_Geo",
    "neogeocd": "SNK_-_Neo_Geo_CD",
    "neogeocdjp": "SNK_-_Neo_Geo_CD",
    "nes": "Nintendo_-_Nintendo_Entertainment_System",
    "ngp": "SNK_-_Neo_Geo_Pocket",
    "ngpc": "SNK_-_Neo_Geo_Pocket_Color",
    "odyssey2": "Magnavox_-_Odyssey2",
    "pc88": "NEC_-_PC-8001_-_PC-8801",
    "pc98": "NEC_-_PC-98",
    "pcengine": "NEC_-_PC_Engine_-_TurboGrafx_16",
    "pcenginecd": "NEC_-_PC_Engine_CD_-_TurboGrafx-CD",
    "pcfx": "NEC_-_PC-FX",
    "plus4": "Commodore_-_Plus-4",
    "pokemini": "Nintendo_-_Pokemon_Mini",
    "ps2": "Sony_-_PlayStation_2",
    "ps3": "Sony_-_PlayStation_3",
    "ps4": "Sony_-_PlayStation_4",
    "psp": "Sony_-_PlayStation_Portable",
    "psvita": "Sony_-_PlayStation_Vita",
    "psx": "Sony_-_PlayStation",
    "pv1000": "Casio_-_PV-1000",
    "satellaview": "Nintendo_-_Satellaview",
    "saturn": "Sega_-_Saturn",
    "saturnjp": "Sega_-_Saturn",
    "scummvm": "ScummVM",
    "scv": "Epoch_-_Super_Cassette_Vision",
    "sega32x": "Sega_-_32X",
    "sega32xjp": "Sega_-_32X",
    "sega32xna": "Sega_-_32X",
    "segacd": "Sega_-_Mega-CD_-_Sega_CD",
    "sfc": "Nintendo_-_Super_Nintendo_Entertainment_System",
    "sg-1000": "Sega_-_SG-1000",
    "snes": "Nintendo_-_Super_Nintendo_Entertainment_System",
    "snesna": "Nintendo_-_Super_Nintendo_Entertainment_System",
    "sufami": "Nintendo_-_Sufami_Turbo",
    "supergrafx": "NEC_-_PC_Engine_SuperGrafx",
    "supracan": "Funtech_-_Super_Acan",
    "tg16": "NEC_-_PC_Engine_-_TurboGrafx_16",
    "tg-cd": "NEC_-_PC_Engine_CD_-_TurboGrafx-CD",
    "vectrex": "GCE_-_Vectrex",
    "vic20": "Commodore_-_VIC-20",
    "videopac": "Philips_-_Videopac",
    "virtualboy": "Nintendo_-_Virtual_Boy",
    "wii": "Nintendo_-_Wii",
    "wiiu": "Nintendo_-_Wii_U",
    "wonderswan": "Bandai_-_WonderSwan",
    "wonderswancolor": "Bandai_-_WonderSwan_Color",
    "x1": "Sharp_-_X1",
    "x68000": "Sharp_-_X68000",
    "xbox": "Microsoft_-_Xbox",
    "xbox360": "Microsoft_-_Xbox_360",
    "zx81": "Sinclair_-_ZX_81",
    "zxspectrum": "Sinclair_-_ZX_Spectrum",
}


def clean_title(title: str) -> str:
    """
    Clean a game title by removing file extension and parenthesised tokens.

    Algorithm:
    1. Strip file extension (for ROM filenames)
    2. Repeatedly remove the last parenthesised group until none remain
    3. Trim whitespace

    Args:
        title: The raw title to clean

    Returns:
        The cleaned title
    """
    # Remove file extension
    title = Path(title).stem

    # Repeatedly remove last parenthesised group (including nested ones)
    while True:
        # Find the rightmost opening parenthesis
        last_open = title.rfind("(")
        if last_open == -1:
            break

        # Find the matching closing parenthesis
        paren_count = 0
        close_pos = -1
        for i in range(last_open, len(title)):
            if title[i] == "(":
                paren_count += 1
            elif title[i] == ")":
                paren_count -= 1
                if paren_count == 0:
                    close_pos = i
                    break

        if close_pos == -1:
            # No matching closing parenthesis found, remove from opening to end
            title = title[:last_open]
        else:
            # Remove the parentheses and everything after
            title = title[:last_open]

    # Trim whitespace
    return title.strip()


def apply_region_preference(
    entries: List[Tuple[str, str]], region_priority: List[str] = None
) -> Optional[str]:
    """
    Apply region preference to select the best image URL from multiple entries.

    Args:
        entries: List of (title, url) tuples for the same clean name
        region_priority: List of regions in priority order (default: ["usa", "europe", "world"])

    Returns:
        The preferred image URL, or None if entries is empty
    """
    if not entries:
        return None

    if len(entries) == 1:
        return entries[0][1]

    if region_priority is None:
        region_priority = DEFAULT_REGION_ORDER

    # Check each priority region
    for region in region_priority:
        for title, url in entries:
            # Extract text within parentheses and check for region match
            # Find all text within parentheses
            paren_matches = re.findall(r"\(([^)]+)\)", title)
            # Check if the region appears in any parentheses (case-insensitive)
            for paren_content in paren_matches:
                if region.lower() in paren_content.lower():
                    return url

    # Return first entry if no preferred regions found
    return entries[0][1]


def load_csv_data(
    data_dir: Path, thumbnail_order: List[str] = None, region_priority: List[str] = None
) -> Dict[str, Dict[str, str]]:
    """
    Load CSV data from all console CSV files in the data directory.

    Args:
        data_dir: Path to the data/processed/consoles directory
        thumbnail_order: Priority order for thumbnail types (default: ["snapshot", "boxart", "title_screen"])
        region_priority: Priority order for regions (default: ["usa", "europe", "world"])

    Returns:
        Nested dictionary: {console: {clean_name: image_url}}
    """
    if thumbnail_order is None:
        thumbnail_order = DEFAULT_THUMBNAIL_ORDER

    # Convert user-friendly names to CSV column names
    csv_image_types = [THUMBNAIL_TYPE_MAPPING[t] for t in thumbnail_order]

    image_map = {}

    # Find all CSV files in the directory
    csv_files = list(data_dir.glob("*.csv"))

    for csv_file in csv_files:
        console_name = csv_file.stem
        # Group entries by clean name and image type
        console_entries = defaultdict(lambda: defaultdict(list))

        try:
            with open(csv_file, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    image_map[console_name] = {}
                    continue

                # Parse CSV content manually to handle potential quoting issues
                reader = csv.reader(content.splitlines())

                for row in reader:
                    if len(row) >= 3:
                        image_type, game_title, image_url = row[0], row[1], row[2]

                        # Process entries for the requested image types
                        if image_type in csv_image_types:
                            clean_name = clean_title(game_title)
                            console_entries[clean_name][image_type].append(
                                (game_title, image_url)
                            )

        except Exception:
            # Skip files that can't be read
            continue

        # Apply thumbnail type priority and region preference for each clean name
        console_map = {}
        for clean_name, type_entries in console_entries.items():
            # Try each image type in priority order
            selected_url = None
            for csv_image_type in csv_image_types:
                if csv_image_type in type_entries and type_entries[csv_image_type]:
                    # Apply region preference within this image type
                    selected_url = apply_region_preference(
                        type_entries[csv_image_type], region_priority
                    )
                    if selected_url:
                        break

            if selected_url:
                console_map[clean_name] = selected_url

        image_map[console_name] = console_map

    return image_map


def validate_thumbnail_order(order_string: str) -> List[str]:
    """
    Validate and parse thumbnail order string.

    Args:
        order_string: Comma-separated thumbnail types

    Returns:
        List of validated thumbnail types

    Raises:
        ValueError: If any thumbnail type is invalid
    """
    if not order_string.strip():
        return DEFAULT_THUMBNAIL_ORDER

    types = [t.strip() for t in order_string.split(",")]
    valid_types = set(THUMBNAIL_TYPE_MAPPING.keys())

    for t in types:
        if t not in valid_types:
            raise ValueError(
                f"Invalid thumbnail type '{t}'. Valid types: {', '.join(sorted(valid_types))}"
            )

    # Remove duplicates while preserving order
    seen = set()
    result = []
    for t in types:
        if t not in seen:
            result.append(t)
            seen.add(t)

    return result


def validate_region_priority(priority_string: str) -> List[str]:
    """
    Validate and parse region priority string.

    Args:
        priority_string: Comma-separated region names

    Returns:
        List of region names in lowercase
    """
    if not priority_string.strip():
        return DEFAULT_REGION_ORDER

    # Split by comma, strip whitespace, and convert to lowercase
    regions = [r.strip().lower() for r in priority_string.split(",") if r.strip()]

    # Remove duplicates while preserving order
    seen = set()
    result = []
    for r in regions:
        if r not in seen:
            result.append(r)
            seen.add(r)

    return result if result else DEFAULT_REGION_ORDER


def discover_roms(rom_root: Path) -> Dict[str, Dict[str, Path]]:
    """
    Discover ROM files in a directory structure.

    Expected structure:
    rom_root/
    └─ ConsoleName/
        ├─ Game Title (USA).ext
        └─ Another Game (Europe).ext

    Args:
        rom_root: Root directory containing console subdirectories

    Returns:
        Nested dictionary: {console: {clean_name: absolute_path}}
    """
    rom_map = defaultdict(dict)

    # Find all files in console subdirectories (one level deep)
    rom_files = list(rom_root.glob("*/*"))

    for rom_file in rom_files:
        # Only process files, not directories
        if not rom_file.is_file():
            continue

        raw_console_name = rom_file.parent.name
        # Map the raw console name to the CSV console name
        console_name = CONSOLE_MAPPING.get(raw_console_name, raw_console_name)

        clean_name = clean_title(rom_file.name)

        # Skip files that result in empty clean names
        if not clean_name:
            continue

        # Check for duplicate ROM entries
        if clean_name in rom_map[console_name]:
            print(
                f"Warning: Duplicate ROM found for '{clean_name}' in console '{console_name}'. "
                f"Keeping first entry: {rom_map[console_name][clean_name]}"
            )
            continue

        # Warn if console mapping was not found
        if raw_console_name not in CONSOLE_MAPPING:
            print(
                f"Warning: No console mapping found for ROM folder '{raw_console_name}'. "
                f"Using original name '{raw_console_name}' for matching."
            )

        rom_map[console_name][clean_name] = rom_file.absolute()

    # Only return consoles that have at least one ROM
    return {console: roms for console, roms in rom_map.items() if roms}


def generate_wget_commands(
    image_map: Dict[str, Dict[str, str]], rom_map: Dict[str, Dict[str, Path]]
) -> Generator[str, None, None]:
    """
    Generate wget commands for downloading images matching ROM files.

    Args:
        image_map: {console: {clean_name: image_url}}
        rom_map: {console: {clean_name: rom_path}}

    Yields:
        wget command strings for downloading images
    """
    # Process each console in ROM map
    for console, roms in rom_map.items():
        if console not in image_map:
            print(f"Warning: Console '{console}' not found in CSV data, skipping.")
            continue

        console_images = image_map[console]

        # Process each ROM in the console
        for clean_name, rom_path in roms.items():
            if clean_name not in console_images:
                # Silently ignore ROMs without corresponding images
                continue

            image_url = console_images[clean_name]

            # Determine destination path: same as ROM but with image extension
            # Extract extension from URL, default to .png
            parsed_url = urlparse(image_url)
            url_path = Path(parsed_url.path)
            if url_path.suffix:
                image_ext = url_path.suffix
            else:
                image_ext = ".png"

            dest_path = rom_path.with_suffix(image_ext)

            # Skip if destination already exists
            if dest_path.exists():
                continue

            # Generate wget command with URL encoding and quoted path for whitespace handling
            encoded_url = quote(image_url, safe=":/?#[]@!$&'()*+,;=")
            yield f'wget "{encoded_url}" -O "{dest_path}"'


def main() -> None:
    """
    Main CLI entry point for the ROM thumbnails downloader.
    """
    parser = argparse.ArgumentParser(
        description="Download box art images for your ROM collection from libretro-thumbnails",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Thumbnail types:
  snapshot      In-game snapshots, aka gameplay screenshots
  boxart        Scans of the boxes or covers of games
  title_screen  Images of the game's introductory title screen

Examples:
  %(prog)s /path/to/roms
  %(prog)s /path/to/roms --thumbnail-order boxart
  %(prog)s /path/to/roms --thumbnail-order title_screen,boxart
  %(prog)s /path/to/roms --region-priority japan,usa,europe
  %(prog)s /path/to/roms --thumbnail-order boxart --region-priority brazil,usa
        """,
    )

    parser.add_argument(
        "rom_path", type=Path, help="Path to the ROM collection directory"
    )

    parser.add_argument(
        "--thumbnail-order",
        default=",".join(DEFAULT_THUMBNAIL_ORDER),
        help=f"Priority order for thumbnail types (default: {','.join(DEFAULT_THUMBNAIL_ORDER)}). "
        "Specify 1-3 comma-separated values from: {snapshot, boxart, title_screen}",
    )

    parser.add_argument(
        "--region-priority",
        default=",".join(DEFAULT_REGION_ORDER),
        help=f"Priority order for regions (default: {','.join(DEFAULT_REGION_ORDER)}). "
        "Specify comma-separated region names as they appear in ROM filenames (e.g., usa,europe,japan,brazil)",
    )

    try:
        args = parser.parse_args()

        # Validate thumbnail order
        thumbnail_order = validate_thumbnail_order(args.thumbnail_order)

        # Validate region priority
        region_priority = validate_region_priority(args.region_priority)

        # Define the data directory relative to the package location
        package_dir = Path(__file__).parent
        project_root = package_dir.parent.parent
        data_dir = project_root / "data" / "processed" / "consoles"

        print("Loading CSV data...")
        image_map = load_csv_data(data_dir, thumbnail_order, region_priority)

        print("Discovering ROM files...")
        rom_map = discover_roms(args.rom_path)

        print("Generating wget commands...")
        commands = list(generate_wget_commands(image_map, rom_map))

        if not commands:
            print("No matching images found for ROMs.")
            return

        print(f"Found {len(commands)} images to download:")

        # Display progress bar while printing commands
        for command in tqdm(commands, desc="Processing commands"):
            print(command)

    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
