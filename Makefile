# Run a code formatter, and generate README.md from POD documentation.
all:
	@shfmt -w -s -ln=posix -i 4 -bn support/generate-doc.sh
	@cd support && ./generate-doc.sh
