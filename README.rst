.. image:: sphinx/source/_images/gamma_pytools_logo.png

|

*pytools* is an open source library containing general machine learning and visualisation
utilities for reuse, including:

- Basic tools for API development, supporting documentation, deprecation, and run-time validation
- Support for simulating classification and regression data
- Utilities for constructing complex expressions and rendering them as indented strings
- Support for fitting objects to data, and testing whether an object is fitted
- Parallelization based on the joblib package
- A lean MVC framework for rendering basic visualizations in different styles, e.g., as *matplotlib* charts or as plain text

.. Begin-Badges

|pypi| |conda| |azure_build| |azure_code_cov|
|python_versions| |code_style| |made_with_sphinx_doc| |License_badge|

.. End-Badges


Installation
------------

*pytools*  supports both PyPI and Anaconda.
We recommend to install *pytools* into a dedicated environment.

Anaconda
~~~~~~~~

.. code-block:: sh

    conda create -n pytools
    conda activate pytools
    conda install -c bcg_gamma -c conda-forge gamma-pytools


Pip
~~~

macOS and Linux:
^^^^^^^^^^^^^^^^

.. code-block:: sh

    python -m venv pytools
    source pytools/bin/activate
    pip install gamma-pytools

Windows:
^^^^^^^^

.. code-block:: dosbatch

    python -m venv pytools
    pytools\Scripts\activate.bat
    pip install gamma-pytools


Documentation
-------------

For the *pytools* API reference see the `documentation <https://bcg-x-official.github.io/pytools/>`__.

Changes and additions to new versions are summarized in the `release notes <https://bcg-x-official.github.io/pytools/release_notes.html>`__.


Contributing
------------

*pytools* is stable and is being supported long-term.

Contributions to *pytools* are welcome and appreciated.
For any bug reports or feature requests/enhancements please use the appropriate
`GitHub form <https://github.com/BCG-X-Official/pytools/issues>`_, and if you wish to do so,
please open a PR addressing the issue.

We do ask that for any major changes please discuss these with us first via an issue or
at our team email: FacetTeam@bcg.com.

For further information on contributing please see our `contribution guide
<https://bcg-x-official.github.io/pytools/contribution_guide.html>`_.


License
-------

*pytools* is licensed under Apache 2.0 as described in the
`LICENSE <https://github.com/BCG-X-Official/pytools/blob/develop/LICENSE>`_ file.


BCG GAMMA
---------

We are always on the lookout for passionate and talented data scientists to join the
BCG GAMMA team. If you would like to know more you can find out about BCG GAMMA
`here <https://www.bcg.com/en-gb/beyond-consulting/bcg-gamma/default>`_,
or have a look at
`career opportunities <https://www.bcg.com/en-gb/beyond-consulting/bcg-gamma/careers>`_.

.. Begin-Badges

.. |conda| image:: https://anaconda.org/bcg_gamma/gamma-pytools/badges/version.svg
    :target: https://anaconda.org/BCG_Gamma/gamma-pytools

.. |pypi| image:: https://badge.fury.io/py/gamma-pytools.svg
    :target: https://pypi.org/project/gamma-pytools/

.. |azure_build| image:: https://dev.azure.com/gamma-facet/facet/_apis/build/status/BCG-X-Official.pytools?branchName=develop
   :target: https://dev.azure.com/gamma-facet/facet/_build?definitionId=9&_a=summary

.. |azure_code_cov| image:: https://img.shields.io/azure-devops/coverage/gamma-facet/facet/9/2.1.x
   :target: https://dev.azure.com/gamma-facet/facet/_build?definitionId=9&_a=summary

.. |python_versions| image:: https://img.shields.io/badge/python-3.10|3.11|3.12-blue.svg
    :target: https://www.python.org/downloads/release/python-380/

.. |code_style| image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :target: https://github.com/psf/black

.. |made_with_sphinx_doc| image:: https://img.shields.io/badge/Made%20with-Sphinx-1f425f.svg
    :target: https://bcg-x-official.github.io/pytools/index.html

.. |license_badge| image:: https://img.shields.io/badge/License-Apache%202.0-olivegreen.svg
    :target: https://opensource.org/licenses/Apache-2.0

.. End-Badges