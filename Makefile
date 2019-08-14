VERSION := $(shell python setup.py --version)
PROJECT := $(shell python setup.py --name)

package:
	@echo Creating a .tar.gz package for $(PROJECT) at version $(VERSION)
	tar --exclude=__pycache__ -cvzf $(PROJECT)-$(VERSION).tar.gz src setup.py
	@echo $(PROJECT)-$(VERSION).tar.gz created!