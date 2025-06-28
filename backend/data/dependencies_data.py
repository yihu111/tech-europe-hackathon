from utils.parsers import parse_requirements_txt, parse_pipfile, parse_setup_py, parse_package_json

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
    "java": [
        ("pom.xml", None),        # Maven file, parser not implemented here
        ("build.gradle", None),   # Gradle file, parser not implemented here
    ],
    "c#": [
        ("*.csproj", None),       # C# project files, parser not implemented here
        ("packages.config", None),
    ],
    "php": [
        ("composer.json", parse_package_json),
    ],
    "ruby": [
        ("Gemfile", None),        # Ruby Gemfile, parser not implemented here
        ("Gemfile.lock", None),
    ],
    "go": [
        ("go.mod", None),         # Go modules file
        ("go.sum", None),
    ],
    "kotlin": [
        ("build.gradle.kts", None),  # Kotlin Gradle script
        ("build.gradle", None),
    ],
    "dart": [
        ("pubspec.yaml", None),   # Dart dependency file, no parser here
    ],
    "scala": [
        ("build.sbt", None),      # Scala build file, no parser here
    ],
    "rust": [
        ("Cargo.toml", None),     # Rust package file, no parser here
    ],
    "elixir": [
        ("mix.exs", None),        # Elixir dependency file, no parser here
    ],
    "swift": [
        ("Package.swift", None),  # Swift package file, no parser here
    ],
}
