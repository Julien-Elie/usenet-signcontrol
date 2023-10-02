# Run code formatters, and generate README.md from POD documentation.
all:
	@black --line-length 79 --preview --quiet .
	@shfmt -w -s -ln=posix -i 4 -bn support/generate-doc.sh
	@cd support && ./generate-doc.sh
