from repo_handler import clone_repo, get_useful_files, detect_tech_stack

# A small public repo to test with
url = "https://github.com/realpython/reader"

repo_path = clone_repo(url)
files = get_useful_files(repo_path)
tech = detect_tech_stack(files)

print(f"Found {len(files)} useful files\n")
for f in files:
    print(f"  {f['relative_path']}")

print(f"\nTech Stack Detected:")
print(f"  Languages:    {tech['languages']}")
print(f"  Frameworks:   {tech['frameworks']}")
print(f"  Databases:    {tech['databases']}")
print(f"  Has README:   {tech['has_readme']}")
print(f"  Has Requirements: {tech['has_requirements']}")
print(f"  Has Tests:    {tech['has_tests']}")