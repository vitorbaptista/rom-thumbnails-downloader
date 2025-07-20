.PHONY: install test data

install:
	uv sync
	uv run pre-commit install

test:
	uv run pytest

data: data/processed/consoles.csv
	cat data/processed/consoles.csv | while read console; do \
		make "data/processed/consoles/$$console.csv"; \
	done

data/processed/consoles.csv: data/raw/libretro-thumbnails.json
	jq -r '.[] | select(.size == 0) | (.html_url | split("/") | .[-3])' $< > $@

data/raw/libretro-thumbnails.json:
	curl -s https://api.github.com/repos/libretro-thumbnails/libretro-thumbnails/contents/ > $@

data/processed/consoles/%.csv: data/raw/consoles/%.json
	@console=$(basename $(notdir $@) .csv); \
	jq -r '.tree[] | select(.type == "blob") | [(.path | split("/") | .[0]), (.path | split("/") | .[-1] | split(".") | .[0:-1] | join(".")), ("https://raw.githubusercontent.com/libretro-thumbnails/'"$$console"'/refs/heads/master/" + .path)] | @csv' $< \
		| grep -v .gitignore \
		> $@

data/raw/consoles/%.json:
	curl -sf -w "%{http_code}" https://api.github.com/repos/libretro-thumbnails/$*/git/trees/master?recursive=1 -o $@ \
		| grep -q "^200$$" \
		|| { rm -f $@; echo "curl failed or did not return 200"; exit 1; }
