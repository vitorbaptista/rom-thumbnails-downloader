# Match Screenshots – Product Requirements Document (PRD)

## 1. Purpose
Provide a CLI script (`match_screenshots.py`) that, given a directory containing console-organized ROM files, locates the corresponding box-art images listed in processed CSV data and prints safe `wget` commands to download each image next to its ROM.

## 2. Background & Motivation
Libretro maintains a public thumbnail repository that includes Named_Boxarts for thousands of games. This project already stores pre-processed CSVs (`data/processed/consoles/*.csv`) mapping games to image URLs. Automating the matching & download process will:  
* Save manual effort identifying the correct thumbnail for each ROM.  
* Ensure consistency by preferring regional variants (USA ▸ Europe ▸ World ▸ Other).  
* Prevent accidental overwrites by skipping files that already exist.

## 3. Scope
Covered:  
* Reading CSVs and preparing in-memory maps.  
* Cleaning/normalising game titles for exact matching.  
* Discovering ROM files inside a one-level console folder hierarchy.  
* Generating, **not executing**, `wget` commands to download thumbnails.  
* Displaying a progress bar for processing using `tqdm`.  
Not covered:  
* Download execution and checksum verification.  
* Deeply nested ROM structures (>1 level).  
* Fuzzy matching beyond exact clean names.

## 4. Glossary
* **ROM** – Game binary file (e.g. `.sfc`, `.bin`, `.nes`).  
* **Named_Boxarts** – Image type used in CSVs for front-box artwork.  
* **Clean Name** – Game title with all trailing parenthesised tokens removed (see §6) and trimmed whitespace.

## 5. Data Sources
```
workspace/
└─ data/processed/consoles/*.csv         # Pre-processed thumbnail listings (no header)
      column[0] – image_type (e.g. Named_Boxarts)
      column[1] – game title (raw)
      column[2] – image URL (.png)
```

## 6. Title Cleaning Algorithm
1. Strip file extension (for ROM filenames).  
2. Repeatedly remove the **last** parenthesised group, including its parentheses, until none remain.  
   * Example: `"Game (Rev A) (USA)" → "Game"`.  
3. Trim whitespace.  

### Region Preference (CSV rows)
When multiple CSV entries yield the same Clean Name:
1. Prefer row whose **final** parentheses contain `USA`.  
2. Else prefer `Europe`.  
3. Else prefer `World`.  
4. Else keep the **first** encountered.

## 7. CLI & I/O
```
usage: python match_screenshots.py /path/to/rom_root
```
* **Argument**: Absolute or relative path to a directory structured as:
```
rom_root/
└─ <ConsoleName>/
     ├─ Game Title (USA).ext
     └─ Another Game (Europe).ext
```
* The script may be executed from **any** working directory; Pathlib ensures robust relative handling.

## 8. Processing Flow
1. **Load CSVs**  
   * Iterate `data/processed/consoles/*.csv` (Pathlib).  
   * Parse rows; keep those where `image_type == "Named_Boxarts"`.  
   * Build `image_map: Dict[str, Dict[str, str]]`  
     ```python
     image_map[console][clean_name] = image_url
     ```
2. **Discover ROMs**  
   * Recursively glob `rom_root/*/*` but expect exactly one level of console folder.  
   * For each file, derive `console = parent.name`.  
   * Compute `clean_name` via §6.  
   * Build `rom_map: Dict[str, Dict[str, Path]]`  
     ```python
     rom_map[console][clean_name] = absolute_path
     ```
3. **Match & Emit Commands**  
   * For each `console` in `rom_map`:  
       * For each `clean_name` present in **both** maps:  
           * Determine destination path: same as ROM path but with extension replaced by image URLʼs suffix (usually `.png`).  
           * **Skip** if destination already exists.  
           * Print:
             ```
             wget <image_url> -O <dest_path>
             ```

## 9. Edge Cases & Error Handling
* Console present in ROMs but not in CSVs ▸ warn + skip.  
* Clean name missing on either side ▸ silently ignore.  
* Duplicate ROM matches (same clean name under same console) ▸ warn, keep first.  
* Pre-existing destination file ▸ skip to avoid overwrite.

## 10. Non-Functional Requirements
* Script finishes within a few seconds for directories up to 10k ROMs.  
* Memory footprint < 200 MB.  
* Compatible with Python 3.8+.  
* Displays a responsive progress bar (`tqdm`) throughout processing.  

## 11. Acceptance Criteria
1. Running the script with the ROM sample set prints correct `wget` commands only for games that have a Named_Boxarts entry.  
2. Commands point to the correct console sub-folders and use the ROM filename stem for the output filename.  
3. No command overwrites an existing file (verified by rerunning and seeing fewer/no commands).  
4. Pytest unit tests cover: cleaning algorithm, region preference, CSV loading, ROM discovery, matching logic, and progress bar invocation.  
5. When executed, the script displays a `tqdm` progress bar that reaches 100% upon completion.  

## 12. Future Enhancements
* Execute downloads in parallel.  
* Fuzzy matching (Levenshtein, synonyms).  
* Support multi-level or flat ROM directories.  
* Integrate with checksum databases for verification. 