FACET_PATH := $(abspath $(dir $(lastword $(MAKEFILE_LIST)))/../)
FACET_PATH := $(shell echo "${FACET_PATH}" | sed -e 's/ //g')
export CONDA_BLD_PATH=$(FACET_PATH)/pytools/dist/conda


help:
	@echo Usage: make package

.PHONY: help Makefile

clean:
	mkdir -p "$(CONDA_BLD_PATH)" && \
	rm -rf $(CONDA_BLD_PATH)/*

build:
	echo Creating a conda package for pytools && \
	FACET_PATH="$(FACET_PATH)" conda-build -c conda-forge conda-build/

package: clean build