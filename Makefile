PYTHON ?= .venv/bin/python
export PATH := $(CURDIR)/.venv/bin:$(PATH)
export MPLCONFIGDIR := $(CURDIR)/.cache/matplotlib
export IPYTHONDIR := $(CURDIR)/.cache/ipython
export JUPYTER_PLATFORM_DIRS := 1
TTS_IMAGE ?= spine-learn-tts

.PHONY: notebook site test narration-check narration-status tts-image narration terminology serve
notebook:
	$(PYTHON) -m spine_learn.build notebook
site:
	$(PYTHON) -m spine_learn.build site
serve:
	$(PYTHON) scripts/serve_site.py

test:
	$(PYTHON) -m pytest -q
narration-check:
	$(PYTHON) -m spine_learn.narration validate
narration-status:
	$(PYTHON) -m spine_learn.narration status
tts-image:
	docker build -t $(TTS_IMAGE) tts
narration:
	mkdir -p .cache/kokoro
	docker run --rm --user "$$(id -u):$$(id -g)" -e HOME=/tmp -v "$(CURDIR):/workspace" -v "$(CURDIR)/.cache/kokoro:/models" $(TTS_IMAGE) build
terminology:
	mkdir -p .cache/kokoro
	docker run --rm --user "$$(id -u):$$(id -g)" -e HOME=/tmp -v "$(CURDIR):/workspace" -v "$(CURDIR)/.cache/kokoro:/models" $(TTS_IMAGE) build --narration narration/terminology.yaml --output _build/terminology

.PHONY: benchmark
benchmark:
	mkdir -p .cache/kokoro
	docker run --rm --user "$$(id -u):$$(id -g)" -e HOME=/tmp -e PYTHONPATH=/workspace --entrypoint python -v "$(CURDIR):/workspace" -v "$(CURDIR)/.cache/kokoro:/models" $(TTS_IMAGE) scripts/benchmark_narration.py

.PHONY: lint format
lint:
	$(PYTHON) -m ruff check .
	$(PYTHON) -m ruff format --check .
	$(PYTHON) -m pyright
	$(PYTHON) scripts/check_tutorial.py

format:
	$(PYTHON) -m ruff check --fix .
	$(PYTHON) -m ruff format .

.PHONY: tutor
tutor:
	$(PYTHON) scripts/serve_tutor.py

.PHONY: tutor-key
tutor-key:
	$(PYTHON) scripts/configure_tutor.py

.PHONY: colab
colab:
	$(PYTHON) -m spine_learn.build colab
