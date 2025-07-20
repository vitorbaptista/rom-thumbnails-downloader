#!/usr/bin/env python3
"""
Match Screenshots CLI script for ROM thumbnail downloading.
Matches ROM files with corresponding box-art images from CSV data.
"""

import csv
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Generator
from collections import defaultdict
from urllib.parse import urlparse, quote
import sys
from tqdm import tqdm


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
        last_open = title.rfind('(')
        if last_open == -1:
            break
        
        # Find the matching closing parenthesis
        paren_count = 0
        close_pos = -1
        for i in range(last_open, len(title)):
            if title[i] == '(':
                paren_count += 1
            elif title[i] == ')':
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


def apply_region_preference(entries: List[Tuple[str, str]]) -> Optional[str]:
    """
    Apply region preference to select the best image URL from multiple entries.
    
    Preference order: USA -> Europe -> World -> Other (first encountered)
    
    Args:
        entries: List of (title, url) tuples for the same clean name
        
    Returns:
        The preferred image URL, or None if entries is empty
    """
    if not entries:
        return None
    
    if len(entries) == 1:
        return entries[0][1]
    
    # Check for USA preference
    for title, url in entries:
        if 'usa' in title.lower():
            return url
    
    # Check for Europe preference
    for title, url in entries:
        if 'europe' in title.lower():
            return url
    
    # Check for World preference
    for title, url in entries:
        if 'world' in title.lower():
            return url
    
    # Return first entry if no preferred regions found
    return entries[0][1]


def load_csv_data(data_dir: Path) -> Dict[str, Dict[str, str]]:
    """
    Load CSV data from all console CSV files in the data directory.
    
    Args:
        data_dir: Path to the data/processed/consoles directory
        
    Returns:
        Nested dictionary: {console: {clean_name: image_url}}
    """
    image_map = {}
    
    # Find all CSV files in the directory
    csv_files = list(data_dir.glob("*.csv"))
    
    for csv_file in csv_files:
        console_name = csv_file.stem
        console_entries = defaultdict(list)
        
        try:
            with open(csv_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if not content:
                    image_map[console_name] = {}
                    continue
                
                # Parse CSV content manually to handle potential quoting issues
                reader = csv.reader(content.splitlines())
                
                for row in reader:
                    if len(row) >= 3:
                        image_type, game_title, image_url = row[0], row[1], row[2]
                        
                        # Only process Named_Boxarts entries
                        if image_type == "Named_Boxarts":
                            clean_name = clean_title(game_title)
                            console_entries[clean_name].append((game_title, image_url))
        
        except Exception as e:
            # Skip files that can't be read
            continue
        
        # Apply region preference for each clean name
        console_map = {}
        for clean_name, entries in console_entries.items():
            preferred_url = apply_region_preference(entries)
            if preferred_url:
                console_map[clean_name] = preferred_url
        
        image_map[console_name] = console_map
    
    return image_map


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
        
        console_name = rom_file.parent.name
        clean_name = clean_title(rom_file.name)
        
        # Skip files that result in empty clean names
        if not clean_name:
            continue
        
        # Check for duplicate ROM entries
        if clean_name in rom_map[console_name]:
            print(f"Warning: Duplicate ROM found for '{clean_name}' in console '{console_name}'. "
                  f"Keeping first entry: {rom_map[console_name][clean_name]}")
            continue
        
        rom_map[console_name][clean_name] = rom_file.absolute()
    
    # Only return consoles that have at least one ROM
    return {console: roms for console, roms in rom_map.items() if roms}


def generate_wget_commands(image_map: Dict[str, Dict[str, str]], 
                          rom_map: Dict[str, Dict[str, Path]]) -> Generator[str, None, None]:
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
            encoded_url = quote(image_url, safe=':/?#[]@!$&\'()*+,;=')
            yield f'wget "{encoded_url}" -O "{dest_path}"'


def main() -> None:
    """
    Main CLI entry point for the match_screenshots script.
    
    Usage: python match_screenshots.py /path/to/rom_root
    """
    if len(sys.argv) != 2:
        print("Usage: python match_screenshots.py /path/to/rom_root", file=sys.stderr)
        sys.exit(1)
    
    rom_root = Path(sys.argv[1])
    
    # Define the data directory relative to the script location
    script_dir = Path(__file__).parent
    data_dir = script_dir / "data" / "processed" / "consoles"
    
    print("Loading CSV data...")
    image_map = load_csv_data(data_dir)
    
    print("Discovering ROM files...")
    rom_map = discover_roms(rom_root)
    
    print("Generating wget commands...")
    commands = list(generate_wget_commands(image_map, rom_map))
    
    if not commands:
        print("No matching images found for ROMs.")
        return
    
    print(f"Found {len(commands)} images to download:")
    
    # Display progress bar while printing commands
    for command in tqdm(commands, desc="Processing commands"):
        print(command)


if __name__ == "__main__":
    main()