# Makefile for the JUPITER vs Frontier comparison table.
#
# Targets:
#   make            build comparison.tex (default)
#   make pdf        build comparison.tex + compile to comparison.pdf
#   make clean      remove generated artifacts
#
# The harness reads system descriptions from the samples/ directory via the
# compare.py CLI. All feature extraction and the LaTeX template live in this
# directory; merely rerunning the generator picks up schema/samples changes.

COMPARE := uv run compare.py
JUPITER := ../../descriptions/system-jupiter.json
FRONTIER := ../../descriptions/system-frontier-min.json

# ---------------------------------------------------------------------------
# Sources: the generator, its feature registry/template, and the two inputs
# ---------------------------------------------------------------------------
SOURCES := compare.py features.py template.tex.j2 $(JUPITER) $(FRONTIER)

# ---------------------------------------------------------------------------
# Default target: build the LaTeX table from the system descriptions
# ---------------------------------------------------------------------------
.PHONY: all
all: comparison.tex

comparison.tex: $(SOURCES)
	$(COMPARE) $(JUPITER) $(FRONTIER) -o comparison.tex

# ---------------------------------------------------------------------------
# Compile the PDF from the generated LaTeX
# ---------------------------------------------------------------------------
.PHONY: pdf
pdf: comparison.pdf

comparison.pdf: comparison.tex
	pdflatex -interaction=nonstopmode comparison.tex

# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------
.PHONY: clean
clean:
	rm -f comparison.tex comparison.pdf comparison.aux comparison.log