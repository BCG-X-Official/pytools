#!/bin/bash
conda env create -f environment.yml
conda activate pytools-develop
pre-commit install