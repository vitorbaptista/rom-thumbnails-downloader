import pytest
import sys
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock
from match_screenshots import clean_title, apply_region_preference, load_csv_data, discover_roms, generate_wget_commands, main


class TestTitleCleaning:
    def test_clean_title_removes_file_extension(self):
        assert clean_title("Game Title.sfc") == "Game Title"
        assert clean_title("Another Game.bin") == "Another Game"
        assert clean_title("Test.nes") == "Test"

    def test_clean_title_removes_single_parentheses(self):
        assert clean_title("Game Title (USA)") == "Game Title"
        assert clean_title("Another Game (Europe)") == "Another Game"
        assert clean_title("Test (World)") == "Test"

    def test_clean_title_removes_multiple_parentheses(self):
        assert clean_title("Game (Rev A) (USA)") == "Game"
        assert clean_title("Test (Beta) (Proto) (Europe)") == "Test"
        assert clean_title("Complex (V1.1) (Rev B) (USA) (En)") == "Complex"

    def test_clean_title_removes_extension_and_parentheses(self):
        assert clean_title("Game Title (USA).sfc") == "Game Title"
        assert clean_title("Test (Rev A) (Europe).bin") == "Test"

    def test_clean_title_trims_whitespace(self):
        assert clean_title("  Game Title  ") == "Game Title"
        assert clean_title("Game (USA)  ") == "Game"
        assert clean_title("  Test (Europe)") == "Test"

    def test_clean_title_empty_and_edge_cases(self):
        assert clean_title("") == ""
        assert clean_title("   ") == ""
        assert clean_title("Game") == "Game"
        assert clean_title("Game()") == "Game"
        assert clean_title("()") == ""

    def test_clean_title_nested_parentheses(self):
        assert clean_title("Game (Rev (Final)) (USA)") == "Game"
        assert clean_title("Test ((Beta)) (Europe)") == "Test"

    def test_clean_title_no_parentheses(self):
        assert clean_title("Simple Game") == "Simple Game"
        assert clean_title("Game Title.sfc") == "Game Title"


class TestRegionPreference:
    def test_apply_region_preference_prefers_usa(self):
        entries = [
            ("Game", "https://example.com/game_eur.png"),
            ("Game (USA)", "https://example.com/game_usa.png"),
            ("Game (World)", "https://example.com/game_world.png"),
        ]
        result = apply_region_preference(entries)
        assert result == "https://example.com/game_usa.png"

    def test_apply_region_preference_prefers_europe_when_no_usa(self):
        entries = [
            ("Game (Japan)", "https://example.com/game_jp.png"),
            ("Game (Europe)", "https://example.com/game_eur.png"),
            ("Game (World)", "https://example.com/game_world.png"),
        ]
        result = apply_region_preference(entries)
        assert result == "https://example.com/game_eur.png"

    def test_apply_region_preference_prefers_world_when_no_usa_europe(self):
        entries = [
            ("Game (Japan)", "https://example.com/game_jp.png"),
            ("Game (Brazil)", "https://example.com/game_br.png"),
            ("Game (World)", "https://example.com/game_world.png"),
        ]
        result = apply_region_preference(entries)
        assert result == "https://example.com/game_world.png"

    def test_apply_region_preference_returns_first_when_no_preferred_regions(self):
        entries = [
            ("Game (Japan)", "https://example.com/game_jp.png"),
            ("Game (Brazil)", "https://example.com/game_br.png"),
            ("Game (Korea)", "https://example.com/game_kr.png"),
        ]
        result = apply_region_preference(entries)
        assert result == "https://example.com/game_jp.png"

    def test_apply_region_preference_single_entry(self):
        entries = [("Game (Japan)", "https://example.com/game_jp.png")]
        result = apply_region_preference(entries)
        assert result == "https://example.com/game_jp.png"

    def test_apply_region_preference_empty_list(self):
        entries = []
        result = apply_region_preference(entries)
        assert result is None

    def test_apply_region_preference_case_insensitive(self):
        entries = [
            ("Game (europe)", "https://example.com/game_eur.png"),
            ("Game (usa)", "https://example.com/game_usa.png"),
        ]
        result = apply_region_preference(entries)
        assert result == "https://example.com/game_usa.png"


class TestCSVLoading:
    @patch('match_screenshots.Path.glob')
    @patch('builtins.open', new_callable=mock_open)
    def test_load_csv_data_single_file(self, mock_file, mock_glob):
        # Mock CSV content
        csv_content = '"Named_Boxarts","Game Title (USA)","https://example.com/game.png"\n"Snapshots","Other Title","https://example.com/other.png"'
        mock_file.return_value.read.return_value = csv_content
        
        # Mock glob to return one CSV file
        mock_csv_path = MagicMock()
        mock_csv_path.stem = "Console_Name"
        mock_glob.return_value = [mock_csv_path]
        
        result = load_csv_data(Path("/fake/data/processed/consoles"))
        
        expected = {
            "Console_Name": {
                "Game Title": "https://example.com/game.png"
            }
        }
        assert result == expected

    @patch('match_screenshots.Path.glob')
    @patch('builtins.open', new_callable=mock_open)
    def test_load_csv_data_filters_named_boxarts_only(self, mock_file, mock_glob):
        csv_content = '"Named_Boxarts","Game (USA)","https://example.com/game.png"\n"Snapshots","Game (USA)","https://example.com/snapshot.png"\n"Named_Boxarts","Another Game","https://example.com/another.png"'
        mock_file.return_value.read.return_value = csv_content
        
        mock_csv_path = MagicMock()
        mock_csv_path.stem = "Console"
        mock_glob.return_value = [mock_csv_path]
        
        result = load_csv_data(Path("/fake/data"))
        
        expected = {
            "Console": {
                "Game": "https://example.com/game.png",
                "Another Game": "https://example.com/another.png"
            }
        }
        assert result == expected

    @patch('match_screenshots.Path.glob')
    @patch('builtins.open', new_callable=mock_open)
    def test_load_csv_data_applies_region_preference(self, mock_file, mock_glob):
        csv_content = '"Named_Boxarts","Game (Europe)","https://example.com/game_eur.png"\n"Named_Boxarts","Game (USA)","https://example.com/game_usa.png"\n"Named_Boxarts","Game (World)","https://example.com/game_world.png"'
        mock_file.return_value.read.return_value = csv_content
        
        mock_csv_path = MagicMock()
        mock_csv_path.stem = "Console"
        mock_glob.return_value = [mock_csv_path]
        
        result = load_csv_data(Path("/fake/data"))
        
        expected = {
            "Console": {
                "Game": "https://example.com/game_usa.png"
            }
        }
        assert result == expected

    @patch('match_screenshots.Path.glob')
    @patch('builtins.open', new_callable=mock_open)
    def test_load_csv_data_multiple_consoles(self, mock_file, mock_glob):
        csv_content = '"Named_Boxarts","Game Title","https://example.com/game.png"'
        mock_file.return_value.read.return_value = csv_content
        
        console1 = MagicMock()
        console1.stem = "Console1"
        console2 = MagicMock()
        console2.stem = "Console2"
        mock_glob.return_value = [console1, console2]
        
        result = load_csv_data(Path("/fake/data"))
        
        expected = {
            "Console1": {
                "Game Title": "https://example.com/game.png"
            },
            "Console2": {
                "Game Title": "https://example.com/game.png"
            }
        }
        assert result == expected

    @patch('match_screenshots.Path.glob')
    def test_load_csv_data_no_csv_files(self, mock_glob):
        mock_glob.return_value = []
        
        result = load_csv_data(Path("/fake/data"))
        
        assert result == {}

    @patch('match_screenshots.Path.glob')
    @patch('builtins.open', new_callable=mock_open)
    def test_load_csv_data_empty_csv_file(self, mock_file, mock_glob):
        mock_file.return_value.read.return_value = ""
        
        mock_csv_path = MagicMock()
        mock_csv_path.stem = "Console"
        mock_glob.return_value = [mock_csv_path]
        
        result = load_csv_data(Path("/fake/data"))
        
        expected = {"Console": {}}
        assert result == expected


class TestROMDiscovery:
    @patch('match_screenshots.Path.glob')
    def test_discover_roms_single_console(self, mock_glob):
        # Mock ROM files
        mock_rom1 = MagicMock()
        mock_rom1.parent.name = "Sega Genesis"
        mock_rom1.name = "Sonic (USA).bin"
        mock_rom1.absolute.return_value = Path("/roms/Sega Genesis/Sonic (USA).bin")
        
        mock_rom2 = MagicMock()
        mock_rom2.parent.name = "Sega Genesis"
        mock_rom2.name = "Street Fighter (Europe).bin"
        mock_rom2.absolute.return_value = Path("/roms/Sega Genesis/Street Fighter (Europe).bin")
        
        mock_glob.return_value = [mock_rom1, mock_rom2]
        
        result = discover_roms(Path("/roms"))
        
        expected = {
            "Sega Genesis": {
                "Sonic": Path("/roms/Sega Genesis/Sonic (USA).bin"),
                "Street Fighter": Path("/roms/Sega Genesis/Street Fighter (Europe).bin")
            }
        }
        assert result == expected

    @patch('match_screenshots.Path.glob')
    def test_discover_roms_multiple_consoles(self, mock_glob):
        mock_rom1 = MagicMock()
        mock_rom1.parent.name = "NES"
        mock_rom1.name = "Mario Bros.nes"
        mock_rom1.absolute.return_value = Path("/roms/NES/Mario Bros.nes")
        
        mock_rom2 = MagicMock()
        mock_rom2.parent.name = "SNES"
        mock_rom2.name = "Super Mario World (USA).sfc"
        mock_rom2.absolute.return_value = Path("/roms/SNES/Super Mario World (USA).sfc")
        
        mock_glob.return_value = [mock_rom1, mock_rom2]
        
        result = discover_roms(Path("/roms"))
        
        expected = {
            "NES": {
                "Mario Bros": Path("/roms/NES/Mario Bros.nes")
            },
            "SNES": {
                "Super Mario World": Path("/roms/SNES/Super Mario World (USA).sfc")
            }
        }
        assert result == expected

    @patch('match_screenshots.Path.glob')
    def test_discover_roms_handles_duplicate_clean_names(self, mock_glob):
        mock_rom1 = MagicMock()
        mock_rom1.parent.name = "Genesis"
        mock_rom1.name = "Game (USA).bin"
        mock_rom1.absolute.return_value = Path("/roms/Genesis/Game (USA).bin")
        
        mock_rom2 = MagicMock()
        mock_rom2.parent.name = "Genesis"
        mock_rom2.name = "Game (Europe).bin"
        mock_rom2.absolute.return_value = Path("/roms/Genesis/Game (Europe).bin")
        
        mock_glob.return_value = [mock_rom1, mock_rom2]
        
        with patch('builtins.print') as mock_print:
            result = discover_roms(Path("/roms"))
        
        # Should keep the first one and warn about the duplicate
        expected = {
            "Genesis": {
                "Game": Path("/roms/Genesis/Game (USA).bin")
            }
        }
        assert result == expected
        mock_print.assert_called_once()
        assert "Warning: Duplicate ROM" in str(mock_print.call_args)

    @patch('match_screenshots.Path.glob')
    def test_discover_roms_no_roms_found(self, mock_glob):
        mock_glob.return_value = []
        
        result = discover_roms(Path("/empty"))
        
        assert result == {}

    @patch('match_screenshots.Path.glob')
    def test_discover_roms_filters_files_only(self, mock_glob):
        mock_rom = MagicMock()
        mock_rom.parent.name = "NES"
        mock_rom.name = "Game.nes"
        mock_rom.absolute.return_value = Path("/roms/NES/Game.nes")
        mock_rom.is_file.return_value = True
        
        mock_dir = MagicMock()
        mock_dir.is_file.return_value = False
        
        mock_glob.return_value = [mock_rom, mock_dir]
        
        result = discover_roms(Path("/roms"))
        
        expected = {
            "NES": {
                "Game": Path("/roms/NES/Game.nes")
            }
        }
        assert result == expected

    @patch('match_screenshots.Path.glob')
    def test_discover_roms_empty_clean_name_ignored(self, mock_glob):
        mock_rom = MagicMock()
        mock_rom.parent.name = "NES"
        mock_rom.name = "().nes"  # This will result in empty clean name
        mock_rom.absolute.return_value = Path("/roms/NES/().nes")
        mock_rom.is_file.return_value = True
        
        mock_glob.return_value = [mock_rom]
        
        result = discover_roms(Path("/roms"))
        
        expected = {}
        assert result == expected


class TestCommandGeneration:
    def test_generate_wget_commands_successful_match(self):
        image_map = {
            "Genesis": {
                "Sonic": "https://example.com/sonic.png",
                "Street Fighter": "https://example.com/sf.png"
            }
        }
        
        rom_map = {
            "Genesis": {
                "Sonic": Path("/roms/Genesis/Sonic (USA).bin"),
                "Street Fighter": Path("/roms/Genesis/Street Fighter (Europe).bin")
            }
        }
        
        with patch('match_screenshots.Path.exists', return_value=False):
            commands = list(generate_wget_commands(image_map, rom_map))
        
        expected = [
            'wget "https://example.com/sonic.png" -O "/roms/Genesis/Sonic (USA).png"',
            'wget "https://example.com/sf.png" -O "/roms/Genesis/Street Fighter (Europe).png"'
        ]
        assert commands == expected

    def test_generate_wget_commands_skips_existing_files(self):
        image_map = {
            "Genesis": {
                "Sonic": "https://example.com/sonic.png"
            }
        }
        
        rom_map = {
            "Genesis": {
                "Sonic": Path("/roms/Genesis/Sonic (USA).bin")
            }
        }
        
        # Mock that the destination file already exists
        with patch('match_screenshots.Path.exists', return_value=True):
            commands = list(generate_wget_commands(image_map, rom_map))
        
        assert commands == []

    def test_generate_wget_commands_extracts_extension_from_url(self):
        image_map = {
            "NES": {
                "Mario": "https://example.com/mario.jpg"
            }
        }
        
        rom_map = {
            "NES": {
                "Mario": Path("/roms/NES/Mario Bros.nes")
            }
        }
        
        with patch('match_screenshots.Path.exists', return_value=False):
            commands = list(generate_wget_commands(image_map, rom_map))
        
        expected = [
            'wget "https://example.com/mario.jpg" -O "/roms/NES/Mario Bros.jpg"'
        ]
        assert commands == expected

    def test_generate_wget_commands_defaults_to_png_extension(self):
        image_map = {
            "NES": {
                "Mario": "https://example.com/mario"  # No extension
            }
        }
        
        rom_map = {
            "NES": {
                "Mario": Path("/roms/NES/Mario Bros.nes")
            }
        }
        
        with patch('match_screenshots.Path.exists', return_value=False):
            commands = list(generate_wget_commands(image_map, rom_map))
        
        expected = [
            'wget "https://example.com/mario" -O "/roms/NES/Mario Bros.png"'
        ]
        assert commands == expected

    def test_generate_wget_commands_console_mismatch(self):
        image_map = {
            "Genesis": {
                "Sonic": "https://example.com/sonic.png"
            }
        }
        
        rom_map = {
            "SNES": {
                "Mario": Path("/roms/SNES/Mario.sfc")
            }
        }
        
        with patch('match_screenshots.Path.exists', return_value=False):
            commands = list(generate_wget_commands(image_map, rom_map))
        
        assert commands == []

    def test_generate_wget_commands_partial_game_matches(self):
        image_map = {
            "Genesis": {
                "Sonic": "https://example.com/sonic.png",
                "Streets of Rage": "https://example.com/sor.png"
            }
        }
        
        rom_map = {
            "Genesis": {
                "Sonic": Path("/roms/Genesis/Sonic.bin"),
                "Altered Beast": Path("/roms/Genesis/Altered Beast.bin")
            }
        }
        
        with patch('match_screenshots.Path.exists', return_value=False):
            commands = list(generate_wget_commands(image_map, rom_map))
        
        expected = [
            'wget "https://example.com/sonic.png" -O "/roms/Genesis/Sonic.png"'
        ]
        assert commands == expected

    def test_generate_wget_commands_warns_missing_console(self):
        image_map = {
            "Genesis": {
                "Sonic": "https://example.com/sonic.png"
            }
        }
        
        rom_map = {
            "SNES": {
                "Mario": Path("/roms/SNES/Mario.sfc")
            },
            "NES": {
                "Zelda": Path("/roms/NES/Zelda.nes")
            }
        }
        
        with patch('match_screenshots.Path.exists', return_value=False), \
             patch('builtins.print') as mock_print:
            commands = list(generate_wget_commands(image_map, rom_map))
        
        assert commands == []
        # Should warn about missing consoles
        assert mock_print.call_count == 2
        call_args = [str(call) for call in mock_print.call_args_list]
        assert any("SNES" in arg and "not found in CSV data" in arg for arg in call_args)
        assert any("NES" in arg and "not found in CSV data" in arg for arg in call_args)

    def test_generate_wget_commands_quotes_paths_with_whitespace(self):
        image_map = {
            "Genesis": {
                "Sonic Adventure": "https://example.com/sonic.png"
            }
        }
        
        rom_map = {
            "Genesis": {
                "Sonic Adventure": Path("/roms/Genesis/Sonic Adventure (USA).bin")
            }
        }
        
        with patch('match_screenshots.Path.exists', return_value=False):
            commands = list(generate_wget_commands(image_map, rom_map))
        
        expected = [
            'wget "https://example.com/sonic.png" -O "/roms/Genesis/Sonic Adventure (USA).png"'
        ]
        assert commands == expected

    def test_generate_wget_commands_encodes_url_with_spaces(self):
        image_map = {
            "Genesis": {
                "Game": "https://example.com/path with spaces/game image.png"
            }
        }
        
        rom_map = {
            "Genesis": {
                "Game": Path("/roms/Genesis/Game.bin")
            }
        }
        
        with patch('match_screenshots.Path.exists', return_value=False):
            commands = list(generate_wget_commands(image_map, rom_map))
        
        expected = [
            'wget "https://example.com/path%20with%20spaces/game%20image.png" -O "/roms/Genesis/Game.png"'
        ]
        assert commands == expected


class TestCLIInterface:
    @patch('match_screenshots.load_csv_data')
    @patch('match_screenshots.discover_roms')
    @patch('match_screenshots.generate_wget_commands')
    @patch('sys.argv', ['match_screenshots.py', '/rom/path'])
    def test_main_successful_execution(self, mock_gen_commands, mock_discover, mock_load_csv):
        # Mock data
        image_map = {"Genesis": {"Sonic": "https://example.com/sonic.png"}}
        rom_map = {"Genesis": {"Sonic": Path("/roms/Genesis/Sonic.bin")}}
        commands = ['wget "https://example.com/sonic.png" -O "/roms/Genesis/Sonic.png"']
        
        mock_load_csv.return_value = image_map
        mock_discover.return_value = rom_map
        mock_gen_commands.return_value = iter(commands)
        
        with patch('builtins.print') as mock_print:
            main()
        
        # Verify function calls
        mock_load_csv.assert_called_once()
        mock_discover.assert_called_once_with(Path('/rom/path'))
        mock_gen_commands.assert_called_once_with(image_map, rom_map)
        
        # Verify wget commands were printed
        mock_print.assert_called_with('wget "https://example.com/sonic.png" -O "/roms/Genesis/Sonic.png"')

    @patch('sys.argv', ['match_screenshots.py'])
    def test_main_missing_argument(self):
        with pytest.raises(SystemExit):
            main()

    @patch('match_screenshots.tqdm')
    @patch('match_screenshots.load_csv_data')
    @patch('match_screenshots.discover_roms')
    @patch('match_screenshots.generate_wget_commands')
    @patch('sys.argv', ['match_screenshots.py', '/nonexistent/path'])
    def test_main_nonexistent_rom_directory(self, mock_gen_commands, mock_discover, mock_load_csv, mock_tqdm):
        mock_load_csv.return_value = {}
        mock_discover.return_value = {}
        mock_gen_commands.return_value = iter([])
        
        mock_tqdm_instance = MagicMock()
        mock_tqdm.return_value = mock_tqdm_instance
        mock_tqdm_instance.__enter__.return_value = mock_tqdm_instance
        mock_tqdm_instance.__exit__.return_value = None
        
        # Should not crash even with nonexistent directory
        main()
        
        mock_discover.assert_called_once_with(Path('/nonexistent/path'))

    @patch('match_screenshots.tqdm')
    @patch('match_screenshots.load_csv_data')
    @patch('match_screenshots.discover_roms')
    @patch('match_screenshots.generate_wget_commands')
    @patch('sys.argv', ['match_screenshots.py', 'relative/path'])
    def test_main_handles_relative_path(self, mock_gen_commands, mock_discover, mock_load_csv, mock_tqdm):
        mock_load_csv.return_value = {}
        mock_discover.return_value = {}
        mock_gen_commands.return_value = iter([])
        
        mock_tqdm_instance = MagicMock()
        mock_tqdm.return_value = mock_tqdm_instance
        mock_tqdm_instance.__enter__.return_value = mock_tqdm_instance
        mock_tqdm_instance.__exit__.return_value = None
        
        main()
        
        # Should handle relative paths correctly
        mock_discover.assert_called_once_with(Path('relative/path'))
        

class TestIntegration:
    def test_integration_with_fixture_data(self):
        """
        Integration test using actual fixture ROMs and CSV data.
        
        Test fixtures include:
        - Sega Genesis: 4 ROMs (3 in CSV, 1 not in CSV), 1 existing PNG
        - Nintendo SNES: 5 ROMs (4 in CSV, 1 not in CSV), 1 existing PNG
        """
        from pathlib import Path
        import subprocess
        import os
        
        # Get the absolute path to the fixture directory  
        project_root = Path(__file__).parent  # test file is in project root
        fixture_path = project_root / "tests" / "fixtures" / "roms"
        
        # Run the script with fixture data
        result = subprocess.run(
            [
                "uv", "run", "python", "match_screenshots.py", str(fixture_path)
            ],
            capture_output=True,
            text=True,
            cwd=project_root  # Run from project root
        )
        
        # Verify the script ran successfully
        assert result.returncode == 0, f"Script failed with stderr: {result.stderr}"
        
        # Split output into lines for analysis
        output_lines = result.stdout.strip().split('\n')
        
        # Find lines that contain wget commands
        wget_commands = [line for line in output_lines if line.startswith('wget')]
        
        # Expected wget commands based on our fixture data:
        # Note: Commands order may vary, so we check for presence rather than exact order
        expected_patterns = [
            # SNES ROMs that should have matches (excluding Super Mario World which has existing PNG)
            "Donkey Kong Country (USA) (Rev 1).png",
            "Secret of Mana (USA) (Virtual Console).png",
            "Final Fantasy III (USA) (Beta).png", 
            "Legend of Zelda, The - A Link to the Past (USA).png",
            
            # Genesis ROMs that should have matches (excluding 3 Ninjas which has existing PNG)
            "6-Pak (USA).png",
            "ATP Tour Championship Tennis (USA).png",  # Uses USA preference over Europe
            "688 Attack Sub (USA).png"
        ]
        
        # Verify we got some wget commands
        assert len(wget_commands) > 0, "No wget commands found in output"
        
        # Verify each expected command pattern appears in the output
        # Check that each ROM has a corresponding wget command with proper quoting
        wget_output = '\n'.join(wget_commands)
        
        # Verify all commands start with 'wget "' and have '-O "' (proper quoting)
        for cmd in wget_commands:
            assert cmd.startswith('wget "'), f"Command should start with 'wget \"': {cmd}"
            assert '-O "' in cmd, f"Command should contain '-O \"': {cmd}"
            assert cmd.endswith('"'), f"Command should end with quote: {cmd}"
        
        # Verify specific game titles appear in the output paths
        expected_games = [
            "Donkey Kong Country (USA).png",
            "Secret of Mana (USA).png", 
            "Final Fantasy III (USA).png",
            "Legend of Zelda, The - A Link to the Past (USA).png",
            "6-Pak (USA).png",
            "ATP Tour Championship Tennis (Europe).png",  # Note: uses Europe ROM but USA URL
            "688 Attack Sub (USA).png"
        ]
        
        for expected_game in expected_games:
            assert any(expected_game in cmd for cmd in wget_commands), \
                f"Expected game '{expected_game}' not found in wget commands: {wget_commands}"
        
        # Verify duplicate ROM warnings appear in stdout
        warning_lines = [line for line in output_lines if 'Warning: Duplicate ROM' in line]
        
        # Should have warnings for the duplicate ROMs (ROMs with same clean names as existing PNGs)
        assert len(warning_lines) >= 1, f"Expected duplicate ROM warnings, got output: {result.stdout}"
        
        # Verify the script reports the correct number of images to download
        found_lines = [line for line in output_lines if 'Found' in line and 'images to download' in line]
        assert len(found_lines) == 1, f"Expected exactly one 'Found X images to download' line, got: {found_lines}"
        
        # Extract number of images found
        found_line = found_lines[0]
        import re
        match = re.search(r'Found (\d+) images to download', found_line)
        assert match, f"Could not parse number from: {found_line}"
        
        num_images = int(match.group(1))
        # Should find images for ROMs that:
        # 1. Exist in CSV data 
        # 2. Don't already have PNG files
        # Based on our fixtures, this should be exactly 7 commands
        assert num_images == 7, f"Expected 7 images to download, got {num_images}"
        
        # Verify actual number of wget commands matches reported number
        assert len(wget_commands) == num_images, \
            f"Number of wget commands ({len(wget_commands)}) doesn't match reported number ({num_images})"