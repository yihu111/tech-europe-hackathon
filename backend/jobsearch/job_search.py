async def run_job_search(languages: dict, frameworks: list[str]):
    # Extract list of language names only
    language_list = list(languages.keys())

    # Flatten both into a unified technology stack list (lowercased for consistency)
    tech_stack = [lang.lower() for lang in language_list] + [fw.lower() for fw in frameworks]

    # OPTIONAL: print for debugging
    print("Languages:", language_list)
    print("Frameworks:", frameworks)
    print("Combined tech stack:", tech_stack)

    # Here you can plug into your job matching logic
    return {
        "language_list": language_list,
        "framework_list": frameworks,
        "tech_stack": tech_stack
    }
