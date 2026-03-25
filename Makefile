# Repository Makefile
#
# The Makefile provides standard development commands for the repository.
#
# The command `make ci` is the repository validation entry point used by:
# - developers
# - CI pipelines
# - AI agents

.PHONY: ci smoke

ci: smoke
	@echo ""
	@echo "CI validation completed successfully."

smoke:
	@./tests/smoke_test.sh
