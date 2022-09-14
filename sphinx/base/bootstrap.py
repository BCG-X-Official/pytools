def run_make(*, branch: str, working_directory: str) -> None:
    from typing import List, Tuple

    class Bootstrapper:
        # URI of pytools raw file storage on GitHub
        GITHUB_ROOT_URL = "https://raw.githubusercontent.com/BCG-Gamma/pytools"

        # paths relative to pytools/sphinx
        PATH_MAKE_BASE = ["base"]
        PATH_STATIC_BASE = [*PATH_MAKE_BASE, "_static"]
        PATH_CSS = [*PATH_STATIC_BASE, "css"]
        PATH_JS = [*PATH_STATIC_BASE, "js"]
        PATH_TEMPLATES_BASE = [*PATH_MAKE_BASE, "_templates"]

        # path/filename pairs of files to load from the pytools repo
        FILES_TO_LOAD: List[Tuple[List[str], str]] = [
            (PATH_MAKE_BASE, "conf_base.py"),
            (PATH_MAKE_BASE, "make_base.py"),
            (PATH_MAKE_BASE, "make_util.py"),
            (PATH_STATIC_BASE, "gamma_logo.png"),
            (PATH_CSS, "gamma.css"),
            (PATH_JS, "gamma.js"),
            (PATH_TEMPLATES_BASE, "custom-class-template.rst"),
            (PATH_TEMPLATES_BASE, "custom-module-template.rst"),
            (PATH_TEMPLATES_BASE, "getting-started-header.rst"),
        ]

        # we only re-download files if they are more than an hour old
        CACHE_LIFESPAN = 1 * 60 * 60

        def __init__(self, branch: str) -> None:
            super().__init__()
            self.branch = branch

        def run(self) -> None:
            import os
            import sys

            for file_location in self.FILES_TO_LOAD:
                self._load_file(*file_location)

            make_path = os.path.realpath(
                os.path.join(working_directory, *self.PATH_MAKE_BASE)
            )
            if make_path not in sys.path:
                sys.path.insert(0, make_path)

        def _load_file(self, path: List[str], filename: str) -> None:
            import os
            import time
            from urllib import request

            target_path = os.path.join(working_directory, *path)
            target_file = os.path.join(target_path, filename)
            if (
                os.path.exists(target_file)
                and os.path.getmtime(target_file) > time.time() - self.CACHE_LIFESPAN
            ):
                # no need to refresh the file
                return

            url = (
                f"{self.GITHUB_ROOT_URL}/{self.branch}/sphinx/"
                f"{'/'.join(path)}/{filename}?raw=true"
            )
            print(f"downloading {url} to {target_file}")
            with request.urlopen(url) as response:
                file_content = response.read()

            os.makedirs(target_path, exist_ok=True)
            with open(target_file, "wb") as f:
                f.write(file_content)

    Bootstrapper(branch).run()
    from make_base import make

    make()
