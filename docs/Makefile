# Generate schema documentation using json-schema-for-humans
# Usage: make            (generate docs, only if schema/config changed)
#        make clean      (remove generated documentation)

SHELL := /bin/bash

# Directory of this Makefile (works no matter where make is invoked from)
MAKE_DIR := $(patsubst %/,%,$(dir $(abspath $(lastword $(MAKEFILE_LIST)))))
REPO_ROOT := $(abspath $(MAKE_DIR)/..)

SCHEMA := $(REPO_ROOT)/schema/system-description-0.5.0.json
CONFIG := $(MAKE_DIR)/generate-docs.json
OUTPUT := $(MAKE_DIR)/index.html

# Artifacts written by generate-schema-doc next to the output
GENERATED := $(OUTPUT) $(MAKE_DIR)/schema_doc.css $(MAKE_DIR)/schema_doc.min.js

GENERATOR := uvx --from json-schema-for-humans generate-schema-doc

.PHONY: all docs clean

all: docs

docs: $(OUTPUT)

$(OUTPUT): $(SCHEMA) $(CONFIG)
	@echo "Generating documentation..."
	@echo "  Schema: $(SCHEMA)"
	@echo "  Output: $(MAKE_DIR)"
	@echo "  Config: $(CONFIG)"
	$(GENERATOR) --config-file "$(CONFIG)" "$(SCHEMA)" "$(OUTPUT)"
	@echo ""
	@echo "Documentation generated: $(OUTPUT)"
	@echo "Open in browser: file://$(OUTPUT)"

clean:
	rm -f $(GENERATED)
