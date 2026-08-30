import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.request import Request, urlopen, urlretrieve

from packaging.tags import sys_tags

if os.name == "linux":
    sys.exit(1)

python_tag = str(next(sys_tags()))

owner = "cgohlke"
repo = "pyicu-build"
version = "2.16.2"

url = f"https://api.github.com/repos/{owner}/{repo}/releases/tags/v{version}"

request = Request(
    url,
    headers={"Accept": "application/vnd.github+json"},
)

with urlopen(request) as response:
    release = json.load(response)

for asset in release["assets"]:
    if python_tag in asset["name"]:
        name, url = asset["name"], asset["browser_download_url"]

with tempfile.TemporaryDirectory() as tmp:
    wheel = Path(tmp) / name  # type: ignore
    urlretrieve(url, wheel)
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            str(wheel),
        ]
    )
