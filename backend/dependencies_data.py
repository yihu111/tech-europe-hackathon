from parsers import parse_requirements_txt, parse_pipfile, parse_setup_py, parse_package_json

LANGUAGE_DEPENDENCY_FILES = {
    "python": [
        ("requirements.txt", parse_requirements_txt),
        ("Pipfile", parse_pipfile),
        ("setup.py", parse_setup_py),
    ],
    "javascript": [
        ("package.json", parse_package_json),
    ],
    "typescript": [
        ("package.json", parse_package_json),
    ],
}