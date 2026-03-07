import os
import sys
import json
from pathlib import Path
from urllib.request import urlopen, urlretrieve
import zipfile
import subprocess
import logging
import tomllib

WORKING_DIRECTORY = Path.home() / "bqt-tmp"

REQUIREMENTS = [
    "PySide6",
    "blender-qt-stylesheet",
]

logger = logging.getLogger("bqt.install")
logger.setLevel(logging.DEBUG)


def download():
    url = "https://api.github.com/repos/techartorg/bqt/releases/latest"
    response = urlopen(url)
    if not response.getcode() == 200:
        raise RuntimeError("Could not retrieve the latest version")

    response_json = json.loads(response.read())
    zip_url = response_json.get("zipball_url")
    zip_url = "https://github.com/Jerakin/bqt/archive/refs/heads/fix/proper-tags.zip"
    if not zip_url:
        raise RuntimeError("Could not retrieve the zipball url")

    tag = response_json.get("tag_name", "")
    name = f"bqt{'-' + tag}.zip"
    urlretrieve(zip_url, name)
    logger.info(f"Downloading to {(Path() / name).resolve()}")
    return Path() / name

def unzip(archive: Path) -> Path:
    location = Path() / archive.stem
    with zipfile.ZipFile(archive, 'r') as zip_ref:
        zip_ref.extractall(location)

    logger.info(f"Unzipped to {location.resolve()}")
    return location

def install_wheels(directory: Path) -> Path:
    def find_project(path: Path) -> Path | None:
        for d in path.iterdir():
            if (d / "bqt").exists():
                return d /"bqt"
            if d.is_dir():
                find_project(d)
        return None

    directory = find_project(directory)
    if directory is None:
        raise RuntimeError("Could not find the bqt project")
    wheels = directory / "wheels"

    subprocess.run([sys.executable, "-m", "pip", "wheel", *REQUIREMENTS, "-w", wheels.as_posix()])
    logger.info(f"Installing wheels to {wheels.resolve()}")
    return directory

def modify_manifest(project: Path) -> None:
    with open(project / "blender_manifest.toml", "a+") as fp:
        content = fp.read()
        content = content + "\n" + "wheels = [\n" + ",\n".join([f'"  ./{x.relative_to(project).as_posix()}"' for x in (project / "wheels").iterdir()]) +"\n]"
        fp.write(content)
    logger.info(f"Manifest changed at {project.resolve()}")


def _build_path(project: Path) -> Path:
    with (project / "blender_manifest.toml").open("rb") as fp:
        toml = tomllib.load(fp)
    return project.parent / f"{toml.get('id')}-{toml.get('version')}.zip"


def build(project: Path) -> Path:
    import bpy

    subprocess.run([bpy.app.binary_path, "--command", "extension", "build", "--source-dir", project.as_posix(), "--output-dir", project.parent.as_posix()])
    logger.info(f"Built extension at {project.resolve()}")
    return _build_path(project)

def install(extension: Path) -> None:
    import bpy
    logger.info(f"Installing extension at {extension.resolve()}")
    bpy.ops.extensions.package_install_files(filepath=extension.resolve().as_posix(), enable_on_install=True, repo = "user_default")


def main():
    WORKING_DIRECTORY.mkdir(parents=True, exist_ok=True)
    os.chdir(WORKING_DIRECTORY)

    zip_file = download()
    # zip_file = Path() / "bqt-2.1.0.zip"
    unzipped = unzip(zip_file)
    project = install_wheels(unzipped)
    modify_manifest(project)
    dist = build(project)
    install(dist)

    # zip_file.unlink()
    # unzipped.unlink()

if __name__ == "__main__":
   main()
