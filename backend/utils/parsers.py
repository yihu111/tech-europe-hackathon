import json
import re

from data.frameworks_data import LANGUAGE_FRAMEWORKS

def parse_package_json(content: str):
    """
    Parse package.json content (JSON) and return list of dependencies.
    Normalizes keys to lowercase.
    """
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return []
    deps = data.get("dependencies", {})
    dev_deps = data.get("devDependencies", {})
    all_deps = {**deps, **dev_deps}
    # Normalize to lowercase
    return [dep.lower() for dep in all_deps.keys()]

def parse_requirements_txt(content: str):
    """
    Parse requirements.txt content, ignoring comments and versions.
    Returns lowercase package names only.
    """
    lines = content.splitlines()
    packages = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # Split on version specifiers and extras like package[extra]==1.0.0
        pkg = re.split(r"[<>=!]", line)[0].strip().lower()
        # Remove extras in square brackets (e.g. package[extra])
        pkg = re.sub(r"\[.*\]", "", pkg)
        packages.append(pkg)
    return packages

def parse_pipfile(content: str):
    packages = []
    current_section = None
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("["):
            current_section = line.lower()
        elif current_section in ("[packages]", "[dev-packages]") and "=" in line:
            pkg = line.split("=")[0].strip().lower()
            packages.append(pkg)
    return packages

def parse_setup_py(content: str):
    pattern = re.compile(r"install_requires\s*=\s*\[(.*?)\]", re.DOTALL)
    match = pattern.search(content)
    if not match:
        return []
    raw_list = match.group(1)
    packages = re.findall(r"['\"]([^'\"]+)['\"]", raw_list)
    return [pkg.lower() for pkg in packages]

def detect_frameworks_by_language(languages: dict, dependencies: list[str]) -> list[str]:
    """
    Given languages detected in the repo and a list of dependencies (package names),
    return a sorted list of matching frameworks.
    """
    found = set()
    deps_lower = [dep.lower() for dep in dependencies]  # normalize once

    for lang in languages.keys():
        lang_lower = lang.lower()
        if lang_lower in LANGUAGE_FRAMEWORKS:
            for fw in LANGUAGE_FRAMEWORKS[lang_lower]:
                if fw.lower() in deps_lower:
                    found.add(fw)
    return sorted(found)
