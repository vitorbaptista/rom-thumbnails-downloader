import pytest
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock
from rom_thumbnails_downloader.cli import (
    clean_title,
    apply_region_preference,
    load_csv_data,
    discover_roms,
    generate_wget_commands,
    validate_thumbnail_order,
    validate_region_priority,
    main,
    DEFAULT_THUMBNAIL_ORDER,
    DEFAULT_REGION_ORDER,
)


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

    def test_apply_region_preference_custom_priority(self):
        entries = [
            ("Game (USA)", "https://example.com/game_usa.png"),
            ("Game (Japan)", "https://example.com/game_jp.png"),
            ("Game (Europe)", "https://example.com/game_eur.png"),
        ]
        # Prefer Japan over USA
        result = apply_region_preference(entries, ["japan", "usa", "europe"])
        assert result == "https://example.com/game_jp.png"

    def test_apply_region_preference_partial_match(self):
        entries = [
            ("Game (Brazil)", "https://example.com/game_br.png"),
            ("Game (USA)", "https://example.com/game_usa.png"),
        ]
        # Search for "bra" should match "Brazil"
        result = apply_region_preference(entries, ["bra", "usa"])
        assert result == "https://example.com/game_br.png"

    def test_apply_region_preference_no_parentheses_ignored(self):
        entries = [
            ("USA Game", "https://example.com/usa_game.png"),
            ("Game (Europe)", "https://example.com/game_eur.png"),
        ]
        # Should not match "USA" in title, only in parentheses
        result = apply_region_preference(entries, ["usa", "europe"])
        assert result == "https://example.com/game_eur.png"

    def test_apply_region_preference_multiple_parentheses(self):
        entries = [
            ("Game (Rev 1) (USA)", "https://example.com/game_usa.png"),
            ("Game (Beta) (Japan)", "https://example.com/game_jp.png"),
        ]
        result = apply_region_preference(entries, ["japan", "usa"])
        assert result == "https://example.com/game_jp.png"


class TestThumbnailOrderValidation:
    def test_validate_thumbnail_order_default_empty(self):
        result = validate_thumbnail_order("")
        assert result == DEFAULT_THUMBNAIL_ORDER

    def test_validate_thumbnail_order_single_type(self):
        result = validate_thumbnail_order("boxart")
        assert result == ["boxart"]

    def test_validate_thumbnail_order_multiple_types(self):
        result = validate_thumbnail_order("title_screen,boxart,snapshot")
        assert result == ["title_screen", "boxart", "snapshot"]

    def test_validate_thumbnail_order_with_spaces(self):
        result = validate_thumbnail_order(" boxart , title_screen ")
        assert result == ["boxart", "title_screen"]

    def test_validate_thumbnail_order_removes_duplicates(self):
        result = validate_thumbnail_order("boxart,boxart,snapshot")
        assert result == ["boxart", "snapshot"]

    def test_validate_thumbnail_order_invalid_type(self):
        with pytest.raises(ValueError, match="Invalid thumbnail type 'invalid'"):
            validate_thumbnail_order("invalid")

    def test_validate_thumbnail_order_mixed_valid_invalid(self):
        with pytest.raises(ValueError, match="Invalid thumbnail type 'bad'"):
            validate_thumbnail_order("boxart,bad,snapshot")


class TestRegionPriorityValidation:
    def test_validate_region_priority_default_empty(self):
        result = validate_region_priority("")
        assert result == DEFAULT_REGION_ORDER

    def test_validate_region_priority_single_region(self):
        result = validate_region_priority("japan")
        assert result == ["japan"]

    def test_validate_region_priority_multiple_regions(self):
        result = validate_region_priority("brazil,usa,korea")
        assert result == ["brazil", "usa", "korea"]

    def test_validate_region_priority_with_spaces(self):
        result = validate_region_priority(" japan , usa , europe ")
        assert result == ["japan", "usa", "europe"]

    def test_validate_region_priority_removes_duplicates(self):
        result = validate_region_priority("usa,japan,usa,europe")
        assert result == ["usa", "japan", "europe"]

    def test_validate_region_priority_case_conversion(self):
        result = validate_region_priority("USA,Europe,JAPAN")
        assert result == ["usa", "europe", "japan"]

    def test_validate_region_priority_empty_items(self):
        result = validate_region_priority("usa,,japan,")
        assert result == ["usa", "japan"]


class TestCSVLoading:
    def test_load_csv_data_single_file_default_order(self):
        # Mock CSV content with multiple image types
        csv_content = '"Named_Boxarts","Game Title (USA)","https://example.com/game_boxart.png"\n"Named_Snaps","Game Title (USA)","https://example.com/game_snap.png"'
        mock_file = mock_open(read_data=csv_content)

        with patch("builtins.open", mock_file), patch(
            "rom_thumbnails_downloader.cli.Path.glob"
        ) as mock_glob:
            mock_csv_path = MagicMock()
            mock_csv_path.stem = "Console_Name"
            mock_glob.return_value = [mock_csv_path]

            # Default order is snapshot, boxart, title_screen - should prefer snapshot
            result = load_csv_data(Path("/fake/data/processed/consoles"))

            expected = {
                "Console_Name": {"Game Title": "https://example.com/game_snap.png"}
            }
            assert result == expected

    def test_load_csv_data_custom_thumbnail_order(self):
        # Mock CSV content with multiple image types
        csv_content = '"Named_Boxarts","Game Title (USA)","https://example.com/game_boxart.png"\n"Named_Snaps","Game Title (USA)","https://example.com/game_snap.png"\n"Named_Titles","Game Title (USA)","https://example.com/game_title.png"'
        mock_file = mock_open(read_data=csv_content)

        with patch("builtins.open", mock_file), patch(
            "rom_thumbnails_downloader.cli.Path.glob"
        ) as mock_glob:
            mock_csv_path = MagicMock()
            mock_csv_path.stem = "Console_Name"
            mock_glob.return_value = [mock_csv_path]

            # Custom order: boxart first
            result = load_csv_data(
                Path("/fake/data/processed/consoles"), ["boxart", "snapshot"]
            )

            expected = {
                "Console_Name": {"Game Title": "https://example.com/game_boxart.png"}
            }
            assert result == expected

    def test_load_csv_data_fallback_to_second_choice(self):
        # Mock CSV content with only title_screen and snapshot (no boxart)
        csv_content = '"Named_Snaps","Game Title (USA)","https://example.com/game_snap.png"\n"Named_Titles","Game Title (USA)","https://example.com/game_title.png"'
        mock_file = mock_open(read_data=csv_content)

        with patch("builtins.open", mock_file), patch(
            "rom_thumbnails_downloader.cli.Path.glob"
        ) as mock_glob:
            mock_csv_path = MagicMock()
            mock_csv_path.stem = "Console_Name"
            mock_glob.return_value = [mock_csv_path]

            # Order: boxart (not available), snapshot (available)
            result = load_csv_data(
                Path("/fake/data/processed/consoles"),
                ["boxart", "snapshot", "title_screen"],
            )

            expected = {
                "Console_Name": {"Game Title": "https://example.com/game_snap.png"}
            }
            assert result == expected

    def test_load_csv_data_filters_by_thumbnail_type(self):
        csv_content = '"Named_Boxarts","Game (USA)","https://example.com/game.png"\n"Named_Snaps","Game (USA)","https://example.com/snapshot.png"\n"Named_Boxarts","Another Game","https://example.com/another.png"'
        mock_file = mock_open(read_data=csv_content)

        with patch("builtins.open", mock_file), patch(
            "rom_thumbnails_downloader.cli.Path.glob"
        ) as mock_glob:
            mock_csv_path = MagicMock()
            mock_csv_path.stem = "Console"
            mock_glob.return_value = [mock_csv_path]

            # Only request boxart images
            result = load_csv_data(Path("/fake/data"), ["boxart"])

            expected = {
                "Console": {
                    "Game": "https://example.com/game.png",
                    "Another Game": "https://example.com/another.png",
                }
            }
            assert result == expected

    def test_load_csv_data_applies_region_preference(self):
        csv_content = '"Named_Boxarts","Game (Europe)","https://example.com/game_eur.png"\n"Named_Boxarts","Game (USA)","https://example.com/game_usa.png"\n"Named_Boxarts","Game (World)","https://example.com/game_world.png"'
        mock_file = mock_open(read_data=csv_content)

        with patch("builtins.open", mock_file), patch(
            "rom_thumbnails_downloader.cli.Path.glob"
        ) as mock_glob:
            mock_csv_path = MagicMock()
            mock_csv_path.stem = "Console"
            mock_glob.return_value = [mock_csv_path]

            result = load_csv_data(Path("/fake/data"), ["boxart"])

            expected = {"Console": {"Game": "https://example.com/game_usa.png"}}
            assert result == expected

    def test_load_csv_data_custom_region_priority(self):
        csv_content = '"Named_Boxarts","Game (Japan)","https://example.com/game_jp.png"\n"Named_Boxarts","Game (USA)","https://example.com/game_usa.png"\n"Named_Boxarts","Game (Brazil)","https://example.com/game_br.png"'
        mock_file = mock_open(read_data=csv_content)

        with patch("builtins.open", mock_file), patch(
            "rom_thumbnails_downloader.cli.Path.glob"
        ) as mock_glob:
            mock_csv_path = MagicMock()
            mock_csv_path.stem = "Console"
            mock_glob.return_value = [mock_csv_path]

            # Custom region priority: Brazil > Japan > USA
            result = load_csv_data(
                Path("/fake/data"), ["boxart"], ["brazil", "japan", "usa"]
            )

            expected = {"Console": {"Game": "https://example.com/game_br.png"}}
            assert result == expected

    @patch("rom_thumbnails_downloader.cli.Path.glob")
    @patch("builtins.open", new_callable=mock_open)
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
            "Console1": {"Game Title": "https://example.com/game.png"},
            "Console2": {"Game Title": "https://example.com/game.png"},
        }
        assert result == expected

    @patch("rom_thumbnails_downloader.cli.Path.glob")
    def test_load_csv_data_no_csv_files(self, mock_glob):
        mock_glob.return_value = []

        result = load_csv_data(Path("/fake/data"))

        assert result == {}

    @patch("rom_thumbnails_downloader.cli.Path.glob")
    @patch("builtins.open", new_callable=mock_open)
    def test_load_csv_data_empty_csv_file(self, mock_file, mock_glob):
        mock_file.return_value.read.return_value = ""

        mock_csv_path = MagicMock()
        mock_csv_path.stem = "Console"
        mock_glob.return_value = [mock_csv_path]

        result = load_csv_data(Path("/fake/data"))

        expected = {"Console": {}}
        assert result == expected


class TestROMDiscovery:
    @patch("rom_thumbnails_downloader.cli.Path.glob")
    def test_discover_roms_single_console(self, mock_glob):
        # Mock ROM files
        mock_rom1 = MagicMock()
        mock_rom1.parent.name = "genesis"
        mock_rom1.name = "Sonic (USA).bin"
        mock_rom1.absolute.return_value = Path("/roms/genesis/Sonic (USA).bin")

        mock_rom2 = MagicMock()
        mock_rom2.parent.name = "genesis"
        mock_rom2.name = "Street Fighter (Europe).bin"
        mock_rom2.absolute.return_value = Path(
            "/roms/genesis/Street Fighter (Europe).bin"
        )

        mock_glob.return_value = [mock_rom1, mock_rom2]

        result = discover_roms(Path("/roms"))

        expected = {
            "Sega_-_Mega_Drive_-_Genesis": {
                "Sonic": Path("/roms/genesis/Sonic (USA).bin"),
                "Street Fighter": Path("/roms/genesis/Street Fighter (Europe).bin"),
            }
        }
        assert result == expected

    @patch("rom_thumbnails_downloader.cli.Path.glob")
    def test_discover_roms_multiple_consoles(self, mock_glob):
        mock_rom1 = MagicMock()
        mock_rom1.parent.name = "nes"
        mock_rom1.name = "Mario Bros.nes"
        mock_rom1.absolute.return_value = Path("/roms/nes/Mario Bros.nes")

        mock_rom2 = MagicMock()
        mock_rom2.parent.name = "snes"
        mock_rom2.name = "Super Mario World (USA).sfc"
        mock_rom2.absolute.return_value = Path("/roms/snes/Super Mario World (USA).sfc")

        mock_glob.return_value = [mock_rom1, mock_rom2]

        result = discover_roms(Path("/roms"))

        expected = {
            "Nintendo_-_Nintendo_Entertainment_System": {
                "Mario Bros": Path("/roms/nes/Mario Bros.nes")
            },
            "Nintendo_-_Super_Nintendo_Entertainment_System": {
                "Super Mario World": Path("/roms/snes/Super Mario World (USA).sfc")
            },
        }
        assert result == expected

    @patch("rom_thumbnails_downloader.cli.Path.glob")
    def test_discover_roms_handles_duplicate_clean_names(self, mock_glob):
        mock_rom1 = MagicMock()
        mock_rom1.parent.name = "genesis"
        mock_rom1.name = "Game (USA).bin"
        mock_rom1.absolute.return_value = Path("/roms/genesis/Game (USA).bin")

        mock_rom2 = MagicMock()
        mock_rom2.parent.name = "genesis"
        mock_rom2.name = "Game (Europe).bin"
        mock_rom2.absolute.return_value = Path("/roms/genesis/Game (Europe).bin")

        mock_glob.return_value = [mock_rom1, mock_rom2]

        with patch("builtins.print") as mock_print:
            result = discover_roms(Path("/roms"))

        # Should keep the first one and warn about the duplicate
        expected = {
            "Sega_-_Mega_Drive_-_Genesis": {
                "Game": Path("/roms/genesis/Game (USA).bin")
            }
        }
        assert result == expected
        # Should have one warning: duplicate ROM (no mapping warning since "genesis" is mapped)
        mock_print.assert_called_once()
        assert "Warning: Duplicate ROM" in str(mock_print.call_args)

    @patch("rom_thumbnails_downloader.cli.Path.glob")
    def test_discover_roms_no_roms_found(self, mock_glob):
        mock_glob.return_value = []

        result = discover_roms(Path("/empty"))

        assert result == {}

    @patch("rom_thumbnails_downloader.cli.Path.glob")
    def test_discover_roms_filters_files_only(self, mock_glob):
        mock_rom = MagicMock()
        mock_rom.parent.name = "nes"
        mock_rom.name = "Game.nes"
        mock_rom.absolute.return_value = Path("/roms/nes/Game.nes")
        mock_rom.is_file.return_value = True

        mock_dir = MagicMock()
        mock_dir.is_file.return_value = False

        mock_glob.return_value = [mock_rom, mock_dir]

        result = discover_roms(Path("/roms"))

        expected = {
            "Nintendo_-_Nintendo_Entertainment_System": {
                "Game": Path("/roms/nes/Game.nes")
            }
        }
        assert result == expected

    @patch("rom_thumbnails_downloader.cli.Path.glob")
    def test_discover_roms_empty_clean_name_ignored(self, mock_glob):
        mock_rom = MagicMock()
        mock_rom.parent.name = "nes"
        mock_rom.name = "().nes"  # This will result in empty clean name
        mock_rom.absolute.return_value = Path("/roms/nes/().nes")
        mock_rom.is_file.return_value = True

        mock_glob.return_value = [mock_rom]

        result = discover_roms(Path("/roms"))

        expected = {}
        assert result == expected


class TestCommandGeneration:
    def test_generate_wget_commands_successful_match(self):
        image_map = {
            "Sega_-_Mega_Drive_-_Genesis": {
                "Sonic": "https://example.com/sonic.png",
                "Street Fighter": "https://example.com/sf.png",
            }
        }

        rom_map = {
            "Sega_-_Mega_Drive_-_Genesis": {
                "Sonic": Path("/roms/genesis/Sonic (USA).bin"),
                "Street Fighter": Path("/roms/genesis/Street Fighter (Europe).bin"),
            }
        }

        with patch("rom_thumbnails_downloader.cli.Path.exists", return_value=False):
            commands = list(generate_wget_commands(image_map, rom_map))

        expected = [
            'wget "https://example.com/sonic.png" -O "/roms/genesis/Sonic (USA).png"',
            'wget "https://example.com/sf.png" -O "/roms/genesis/Street Fighter (Europe).png"',
        ]
        assert commands == expected

    def test_generate_wget_commands_skips_existing_files(self):
        image_map = {
            "Sega_-_Mega_Drive_-_Genesis": {"Sonic": "https://example.com/sonic.png"}
        }

        rom_map = {
            "Sega_-_Mega_Drive_-_Genesis": {
                "Sonic": Path("/roms/genesis/Sonic (USA).bin")
            }
        }

        # Mock that the destination file already exists
        with patch("rom_thumbnails_downloader.cli.Path.exists", return_value=True):
            commands = list(generate_wget_commands(image_map, rom_map))

        assert commands == []

    def test_generate_wget_commands_extracts_extension_from_url(self):
        image_map = {
            "Nintendo_-_Nintendo_Entertainment_System": {
                "Mario": "https://example.com/mario.jpg"
            }
        }

        rom_map = {
            "Nintendo_-_Nintendo_Entertainment_System": {
                "Mario": Path("/roms/nes/Mario Bros.nes")
            }
        }

        with patch("rom_thumbnails_downloader.cli.Path.exists", return_value=False):
            commands = list(generate_wget_commands(image_map, rom_map))

        expected = [
            'wget "https://example.com/mario.jpg" -O "/roms/nes/Mario Bros.jpg"'
        ]
        assert commands == expected

    def test_generate_wget_commands_defaults_to_png_extension(self):
        image_map = {
            "Nintendo_-_Nintendo_Entertainment_System": {
                "Mario": "https://example.com/mario"  # No extension
            }
        }

        rom_map = {
            "Nintendo_-_Nintendo_Entertainment_System": {
                "Mario": Path("/roms/nes/Mario Bros.nes")
            }
        }

        with patch("rom_thumbnails_downloader.cli.Path.exists", return_value=False):
            commands = list(generate_wget_commands(image_map, rom_map))

        expected = ['wget "https://example.com/mario" -O "/roms/nes/Mario Bros.png"']
        assert commands == expected

    def test_generate_wget_commands_console_mismatch(self):
        image_map = {
            "Sega_-_Mega_Drive_-_Genesis": {"Sonic": "https://example.com/sonic.png"}
        }

        rom_map = {
            "Nintendo_-_Super_Nintendo_Entertainment_System": {
                "Mario": Path("/roms/snes/Mario.sfc")
            }
        }

        with patch("rom_thumbnails_downloader.cli.Path.exists", return_value=False):
            commands = list(generate_wget_commands(image_map, rom_map))

        assert commands == []

    def test_generate_wget_commands_partial_game_matches(self):
        image_map = {
            "Sega_-_Mega_Drive_-_Genesis": {
                "Sonic": "https://example.com/sonic.png",
                "Streets of Rage": "https://example.com/sor.png",
            }
        }

        rom_map = {
            "Sega_-_Mega_Drive_-_Genesis": {
                "Sonic": Path("/roms/genesis/Sonic.bin"),
                "Altered Beast": Path("/roms/genesis/Altered Beast.bin"),
            }
        }

        with patch("rom_thumbnails_downloader.cli.Path.exists", return_value=False):
            commands = list(generate_wget_commands(image_map, rom_map))

        expected = ['wget "https://example.com/sonic.png" -O "/roms/genesis/Sonic.png"']
        assert commands == expected

    def test_generate_wget_commands_warns_missing_console(self):
        image_map = {
            "Sega_-_Mega_Drive_-_Genesis": {"Sonic": "https://example.com/sonic.png"}
        }

        rom_map = {
            "Nintendo_-_Super_Nintendo_Entertainment_System": {
                "Mario": Path("/roms/snes/Mario.sfc")
            },
            "Nintendo_-_Nintendo_Entertainment_System": {
                "Zelda": Path("/roms/nes/Zelda.nes")
            },
        }

        with patch(
            "rom_thumbnails_downloader.cli.Path.exists", return_value=False
        ), patch("builtins.print") as mock_print:
            commands = list(generate_wget_commands(image_map, rom_map))

        assert commands == []
        # Should warn about missing consoles
        assert mock_print.call_count == 2
        call_args = [str(call) for call in mock_print.call_args_list]
        assert any(
            "Nintendo_-_Super_Nintendo_Entertainment_System" in arg
            and "not found in CSV data" in arg
            for arg in call_args
        )
        assert any(
            "Nintendo_-_Nintendo_Entertainment_System" in arg
            and "not found in CSV data" in arg
            for arg in call_args
        )

    def test_generate_wget_commands_quotes_paths_with_whitespace(self):
        image_map = {
            "Sega_-_Mega_Drive_-_Genesis": {
                "Sonic Adventure": "https://example.com/sonic.png"
            }
        }

        rom_map = {
            "Sega_-_Mega_Drive_-_Genesis": {
                "Sonic Adventure": Path("/roms/genesis/Sonic Adventure (USA).bin")
            }
        }

        with patch("rom_thumbnails_downloader.cli.Path.exists", return_value=False):
            commands = list(generate_wget_commands(image_map, rom_map))

        expected = [
            'wget "https://example.com/sonic.png" -O "/roms/genesis/Sonic Adventure (USA).png"'
        ]
        assert commands == expected

    def test_generate_wget_commands_encodes_url_with_spaces(self):
        image_map = {
            "Sega_-_Mega_Drive_-_Genesis": {
                "Game": "https://example.com/path with spaces/game image.png"
            }
        }

        rom_map = {
            "Sega_-_Mega_Drive_-_Genesis": {"Game": Path("/roms/genesis/Game.bin")}
        }

        with patch("rom_thumbnails_downloader.cli.Path.exists", return_value=False):
            commands = list(generate_wget_commands(image_map, rom_map))

        expected = [
            'wget "https://example.com/path%20with%20spaces/game%20image.png" -O "/roms/genesis/Game.png"'
        ]
        assert commands == expected


class TestCLIInterface:
    @patch("rom_thumbnails_downloader.cli.load_csv_data")
    @patch("rom_thumbnails_downloader.cli.discover_roms")
    @patch("rom_thumbnails_downloader.cli.generate_wget_commands")
    @patch("sys.argv", ["rom_thumbnails_downloader.cli.py", "/rom/path"])
    def test_main_successful_execution(
        self, mock_gen_commands, mock_discover, mock_load_csv
    ):
        # Mock data
        image_map = {
            "Sega_-_Mega_Drive_-_Genesis": {"Sonic": "https://example.com/sonic.png"}
        }
        rom_map = {
            "Sega_-_Mega_Drive_-_Genesis": {"Sonic": Path("/roms/genesis/Sonic.bin")}
        }
        commands = ['wget "https://example.com/sonic.png" -O "/roms/genesis/Sonic.png"']

        mock_load_csv.return_value = image_map
        mock_discover.return_value = rom_map
        mock_gen_commands.return_value = iter(commands)

        with patch("builtins.print") as mock_print:
            main()

        # Verify function calls
        mock_load_csv.assert_called_once()
        mock_discover.assert_called_once_with(Path("/rom/path"))
        mock_gen_commands.assert_called_once_with(image_map, rom_map)

        # Verify wget commands were printed
        mock_print.assert_called_with(
            'wget "https://example.com/sonic.png" -O "/roms/genesis/Sonic.png"'
        )

    @patch("sys.argv", ["rom_thumbnails_downloader.cli.py"])
    def test_main_missing_argument(self):
        with pytest.raises(SystemExit):
            main()

    @patch("rom_thumbnails_downloader.cli.load_csv_data")
    @patch("rom_thumbnails_downloader.cli.discover_roms")
    @patch("rom_thumbnails_downloader.cli.generate_wget_commands")
    @patch("sys.argv", ["rom_thumbnails_downloader.cli.py", "/nonexistent/path"])
    def test_main_nonexistent_rom_directory(
        self, mock_gen_commands, mock_discover, mock_load_csv
    ):
        mock_load_csv.return_value = {}
        mock_discover.return_value = {}
        mock_gen_commands.return_value = iter([])

        # Should not crash even with nonexistent directory
        main()

        mock_discover.assert_called_once_with(Path("/nonexistent/path"))

    @patch("rom_thumbnails_downloader.cli.load_csv_data")
    @patch("rom_thumbnails_downloader.cli.discover_roms")
    @patch("rom_thumbnails_downloader.cli.generate_wget_commands")
    @patch("sys.argv", ["rom_thumbnails_downloader.cli.py", "relative/path"])
    def test_main_handles_relative_path(
        self, mock_gen_commands, mock_discover, mock_load_csv
    ):
        mock_load_csv.return_value = {}
        mock_discover.return_value = {}
        mock_gen_commands.return_value = iter([])

        main()

        # Should handle relative paths correctly
        mock_discover.assert_called_once_with(Path("relative/path"))

    @patch("rom_thumbnails_downloader.cli.load_csv_data")
    @patch("rom_thumbnails_downloader.cli.discover_roms")
    @patch("rom_thumbnails_downloader.cli.generate_wget_commands")
    @patch(
        "sys.argv",
        [
            "rom_thumbnails_downloader.cli.py",
            "/rom/path",
            "--thumbnail-order",
            "boxart",
        ],
    )
    def test_main_custom_thumbnail_order(
        self, mock_gen_commands, mock_discover, mock_load_csv
    ):
        mock_load_csv.return_value = {}
        mock_discover.return_value = {}
        mock_gen_commands.return_value = iter([])

        main()

        # Verify load_csv_data was called with custom thumbnail order
        mock_load_csv.assert_called_once()
        call_args = mock_load_csv.call_args
        # Second argument should be the thumbnail order
        assert call_args[0][1] == ["boxart"]

    @patch(
        "sys.argv",
        [
            "rom_thumbnails_downloader.cli.py",
            "/rom/path",
            "--thumbnail-order",
            "invalid",
        ],
    )
    def test_main_invalid_thumbnail_order(self):
        with pytest.raises(SystemExit):
            main()

    @patch("rom_thumbnails_downloader.cli.load_csv_data")
    @patch("rom_thumbnails_downloader.cli.discover_roms")
    @patch("rom_thumbnails_downloader.cli.generate_wget_commands")
    @patch(
        "sys.argv",
        [
            "rom_thumbnails_downloader.cli.py",
            "/rom/path",
            "--thumbnail-order",
            "title_screen,boxart",
        ],
    )
    def test_main_multiple_thumbnail_types(
        self, mock_gen_commands, mock_discover, mock_load_csv
    ):
        mock_load_csv.return_value = {}
        mock_discover.return_value = {}
        mock_gen_commands.return_value = iter([])

        main()

        # Verify load_csv_data was called with multiple thumbnail types
        mock_load_csv.assert_called_once()
        call_args = mock_load_csv.call_args
        assert call_args[0][1] == ["title_screen", "boxart"]

    @patch("rom_thumbnails_downloader.cli.load_csv_data")
    @patch("rom_thumbnails_downloader.cli.discover_roms")
    @patch("rom_thumbnails_downloader.cli.generate_wget_commands")
    @patch(
        "sys.argv",
        [
            "rom_thumbnails_downloader.cli.py",
            "/rom/path",
            "--region-priority",
            "japan,usa",
        ],
    )
    def test_main_custom_region_priority(
        self, mock_gen_commands, mock_discover, mock_load_csv
    ):
        mock_load_csv.return_value = {}
        mock_discover.return_value = {}
        mock_gen_commands.return_value = iter([])

        main()

        # Verify load_csv_data was called with custom region priority
        mock_load_csv.assert_called_once()
        call_args = mock_load_csv.call_args
        assert call_args[0][2] == ["japan", "usa"]

    @patch("rom_thumbnails_downloader.cli.load_csv_data")
    @patch("rom_thumbnails_downloader.cli.discover_roms")
    @patch("rom_thumbnails_downloader.cli.generate_wget_commands")
    @patch(
        "sys.argv",
        [
            "rom_thumbnails_downloader.cli.py",
            "/rom/path",
            "--thumbnail-order",
            "boxart",
            "--region-priority",
            "brazil,europe,usa",
        ],
    )
    def test_main_combined_thumbnail_and_region(
        self, mock_gen_commands, mock_discover, mock_load_csv
    ):
        mock_load_csv.return_value = {}
        mock_discover.return_value = {}
        mock_gen_commands.return_value = iter([])

        main()

        # Verify load_csv_data was called with both custom parameters
        mock_load_csv.assert_called_once()
        call_args = mock_load_csv.call_args
        assert call_args[0][1] == ["boxart"]
        assert call_args[0][2] == ["brazil", "europe", "usa"]


class TestIntegration:
    def test_integration_with_fixture_data(self):
        """
        Integration test using actual fixture ROMs and CSV data.

        Test fixtures include:
        - Sega Genesis: 4 ROMs (3 in CSV, 1 not in CSV), 1 existing PNG
        - Nintendo SNES: 5 ROMs (4 in CSV, 1 not in CSV), 1 existing PNG

        With current thumbnail data, expects 7 total downloads (4 SNES + 3 Genesis).
        """
        from pathlib import Path
        import subprocess

        # Get the absolute path to the fixture directory
        test_dir = Path(__file__).parent  # test file is in tests directory
        project_root = test_dir.parent  # go up to project root
        fixture_path = test_dir / "fixtures" / "roms"

        # Run the script with fixture data
        result = subprocess.run(
            [
                "uv",
                "run",
                "python",
                "-m",
                "rom_thumbnails_downloader",
                str(fixture_path),
            ],
            capture_output=True,
            text=True,
            cwd=project_root,  # Run from project root
        )

        # Verify the script ran successfully
        assert result.returncode == 0, f"Script failed with stderr: {result.stderr}"

        # Split stdout and stderr for analysis
        stdout_lines = (
            result.stdout.strip().split("\n") if result.stdout.strip() else []
        )
        stderr_lines = (
            result.stderr.strip().split("\n") if result.stderr.strip() else []
        )

        # Find lines that contain wget commands (should be in stdout)
        wget_commands = [line for line in stdout_lines if line.startswith("wget")]

        # Verify we got some wget commands
        assert len(wget_commands) > 0, "No wget commands found in output"

        # Verify all commands start with 'wget "' and have '-O "' (proper quoting)
        for cmd in wget_commands:
            assert cmd.startswith(
                'wget "'
            ), f"Command should start with 'wget \"': {cmd}"
            assert '-O "' in cmd, f"Command should contain '-O \"': {cmd}"
            assert cmd.endswith('"'), f"Command should end with quote: {cmd}"

        # Verify specific game titles appear in the output paths
        # Should include both Genesis and SNES games
        expected_genesis_games = [
            "6-Pak (USA).png",
            "ATP Tour Championship Tennis (Europe).png",  # Note: uses Europe ROM but USA URL
            "688 Attack Sub (USA).png",
        ]

        expected_snes_games = [
            "Donkey Kong Country (USA).png",
            "Legend of Zelda, The - A Link to the Past (USA).png",
            "Secret of Mana (USA).png",
            "Final Fantasy III (USA).png",
        ]

        all_expected_games = expected_genesis_games + expected_snes_games

        for expected_game in all_expected_games:
            assert any(
                expected_game in cmd for cmd in wget_commands
            ), f"Expected game '{expected_game}' not found in wget commands: {wget_commands}"

        # Verify duplicate ROM warnings appear in stderr
        warning_lines = [
            line for line in stderr_lines if "Warning: Duplicate ROM" in line
        ]

        # Should have warnings for the duplicate ROMs (ROMs with same clean names as existing PNGs)
        assert (
            len(warning_lines) >= 1
        ), f"Expected duplicate ROM warnings, got stderr: {result.stderr}"

        # Verify the script reports the correct number of images to download (in stderr)
        found_lines = [
            line
            for line in stderr_lines
            if "Found" in line and "images to download" in line
        ]
        assert (
            len(found_lines) == 1
        ), f"Expected exactly one 'Found X images to download' line, got: {found_lines}"

        # Extract number of images found
        found_line = found_lines[0]
        import re

        match = re.search(r"Found (\d+) images to download", found_line)
        assert match, f"Could not parse number from: {found_line}"

        num_images = int(match.group(1))
        # Should find images for ROMs that:
        # 1. Exist in CSV data
        # 2. Don't already have PNG files
        # Based on our fixtures: 4 SNES games + 3 Genesis games = 7 total
        assert num_images == 7, f"Expected 7 images to download, got {num_images}"

        # Verify actual number of wget commands matches reported number
        assert (
            len(wget_commands) == num_images
        ), f"Number of wget commands ({len(wget_commands)}) doesn't match reported number ({num_images})"

    def test_integration_with_custom_thumbnail_order(self):
        """
        Integration test using actual fixture ROMs with custom thumbnail order.
        """
        from pathlib import Path
        import subprocess

        # Get the absolute path to the fixture directory
        test_dir = Path(__file__).parent
        project_root = test_dir.parent
        fixture_path = test_dir / "fixtures" / "roms"

        # Run the script with boxart-only order
        result = subprocess.run(
            [
                "uv",
                "run",
                "python",
                "-m",
                "rom_thumbnails_downloader",
                str(fixture_path),
                "--thumbnail-order",
                "boxart",
            ],
            capture_output=True,
            text=True,
            cwd=project_root,
        )

        # Verify the script ran successfully
        assert result.returncode == 0, f"Script failed with stderr: {result.stderr}"

        # Split output into lines for analysis
        stdout_lines = (
            result.stdout.strip().split("\n") if result.stdout.strip() else []
        )

        # Find lines that contain wget commands
        wget_commands = [line for line in stdout_lines if line.startswith("wget")]

        # Should still get the same number of commands since we only have boxart in our test data
        assert (
            len(wget_commands) == 7
        ), f"Expected 7 wget commands with boxart order, got {len(wget_commands)}"

        # Verify all URLs contain "Named_Boxarts" path
        for cmd in wget_commands:
            assert "Named_Boxarts" in cmd, f"Expected boxart URL but got: {cmd}"
