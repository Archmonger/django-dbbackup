# pragma: no cover
# ruff: noqa: PERF401

# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///

import re
import sys

GITHUB_COMPARE_URL_START_RE = r"https?://github.com/[^/]+/[^/]+/compare/"
GITHUB_COMPARE_URL_RE = GITHUB_COMPARE_URL_START_RE + r"([\w.]+)\.\.\.([\w.]+)"
GITHUB_RELEASE_TAG_URL_START_RE = r"https?://github.com/[^/]+/[^/]+/releases/tag/"
GITHUB_RELEASE_TAG_URL_RE = GITHUB_RELEASE_TAG_URL_START_RE + r"([\w.]+)"
UNRELEASED_HEADER = "## [Unreleased]\n"
VERSION_HEADER_START_RE = r"## \[([\w.]+)\]"
VERSION_HEADER_FULL_RE = VERSION_HEADER_START_RE + r" - (\d{4}-\d{2}-\d{2})\n"
UNRELEASED_HYPERLINK_RE = r"\[Unreleased\]: " + GITHUB_COMPARE_URL_RE + r"\n"
VERSION_HYPERLINK_START_RE = r"\[([\w.]+)\]: "
VERSION_HYPERLINK_RE = VERSION_HYPERLINK_START_RE + GITHUB_COMPARE_URL_RE + r"\n"
INITIAL_VERSION_RE = VERSION_HYPERLINK_START_RE + GITHUB_RELEASE_TAG_URL_RE + r"\n"
SECTION_HEADER_RE = r"### ([^\n]+)\n"
HTML_COMMENT_RE = r"<!--.*?-->", re.DOTALL


def validate_changelog(changelog_path="CHANGELOG.md"):
    errors = []
    # Read the contents of the changelog file
    with open(changelog_path, encoding="UTF-8") as file:
        changelog = file.read()

    # Remove markdown comments
    changelog = re.sub(HTML_COMMENT_RE[0], "", changelog, flags=HTML_COMMENT_RE[1])
    # Replace duplicate newlines with a single newline
    changelog = re.sub(r"\n+", "\n", changelog)
    # Replace duplicate spaces with a single space
    changelog = re.sub(r" +", " ", changelog)

    # Ensure `## [Unreleased]\n` is present
    if changelog.find(UNRELEASED_HEADER) == -1:
        errors.append("Changelog does contain '## [Unreleased]'")

    # Ensure unreleased has a URL
    unreleased_url = re.search(UNRELEASED_HYPERLINK_RE, changelog)
    if unreleased_url is None:
        errors.append("Unreleased does not have a URL")

    # Ensure UNRELEASED_URL_REGEX ends in "HEAD"
    if unreleased_url and unreleased_url[2] != "HEAD":
        errors.append(
            f"The hyperlink for [Unreleased] was expected to contain 'HEAD' but instead found '{unreleased_url[2]}'"
        )

    # Ensure the unreleased URL's version is the previous version (version text proceeding [Unreleased])
    if unreleased_url:
        previous_version_linked_in_unreleased = unreleased_url[1]
        previous_version = re.search(r"\[([^\]]+)\] -", changelog)
        if previous_version and previous_version[1] != previous_version_linked_in_unreleased:
            errors.append(
                f"The hyperlink for [Unreleased] was expected to contain '{previous_version[1]}' but instead found '{previous_version_linked_in_unreleased}'"
            )

    # Gather info from version headers. Note that the 'Unreleased' hyperlink is validated separately.
    versions_from_headers = re.findall(VERSION_HEADER_START_RE, changelog)
    versions_from_headers = [header for header in versions_from_headers if header != "Unreleased"]
    dates_from_headers = re.findall(VERSION_HEADER_FULL_RE, changelog)
    dates_from_headers = [header[1] for header in dates_from_headers if header[0] != "Unreleased"]

    # Ensure each version header has a hyperlink
    for version in versions_from_headers:
        if re.search(VERSION_HYPERLINK_START_RE.replace(r"[\w.]+", version), changelog) is None:
            errors.append(f"Version '{version}' does not have a URL")

    # Gather all hyperlinks. Note that the 'Unreleased' hyperlink is validated separately
    hyperlinks = re.findall(VERSION_HYPERLINK_RE, changelog)
    hyperlinks = [hyperlink for hyperlink in hyperlinks if hyperlink[0] != "Unreleased"]

    # Ensure each hyperlink has a header
    for hyperlink in hyperlinks:
        if hyperlink[0] not in versions_from_headers:
            errors.append(f"Hyperlink '{hyperlink[0]}' does not have a version title '## [{hyperlink[0]}]'")

    # Ensure there is only one initial version
    initial_version = re.findall(INITIAL_VERSION_RE, changelog)
    if len(initial_version) > 1:
        errors.append(
            "There is more than one link to a '.../releases/tag/' URL "
            "when this is reserved for only the initial version."
        )

    # Ensure the initial version's tag name matches the version name
    if initial_version:
        initial_version_tag = initial_version[0][0]
        if initial_version_tag != initial_version[0][1]:
            errors.append(
                f"The initial version tag name '{initial_version[0][1]}' does "
                f"not match the version header '{initial_version[0][0]}'"
            )

    # Ensure the initial version has a header
    if (
        initial_version
        and re.search(VERSION_HEADER_START_RE.replace(r"[\w.]+", initial_version[0][0]), changelog) is None
    ):
        errors.append(f"Initial version '{initial_version[0][0]}' does not have a version header")

    # Ensure all versions headers have dates
    full_version_headers = re.findall(VERSION_HEADER_FULL_RE, changelog)
    if len(full_version_headers) != len(versions_from_headers):
        for version in versions_from_headers:
            if re.search(VERSION_HEADER_FULL_RE.replace(r"([\w.]+)", rf"({version})"), changelog) is None:
                errors.append(f"Version header '## [{version}]' does not have a date in the correct format")

    # Ensure version links always diff to the previous version
    versions_from_hyperlinks = [hyperlinks[0] for hyperlinks in hyperlinks]
    versions_from_hyperlinks.append(initial_version[0][0])
    for position, version in enumerate(versions_from_hyperlinks):
        if position == len(versions_from_hyperlinks) - 1:
            break

        pattern = (
            rf"\[{version}\]: {GITHUB_COMPARE_URL_START_RE}{versions_from_hyperlinks[position + 1]}\.\.\.{version}"
        )
        if re.search(pattern, changelog) is None:
            errors.append(
                f"Based on hyperlink order, the URL for version '{version}' was expected to contain '.../compare/{versions_from_hyperlinks[position + 1]}...{version}'"
            )

    # Ensure the versions in the headers are in descending order
    for position, version in enumerate(versions_from_headers):
        if position == len(versions_from_headers) - 1:
            break

        if version <= versions_from_headers[position + 1]:
            errors.append(f"Version '{version}' should be listed before '{versions_from_headers[position + 1]}'")

    # Ensure the order of versions from headers matches the hyperlinks
    for position, version in enumerate(versions_from_headers):
        if position == len(versions_from_headers) - 1:
            break

        if version != versions_from_hyperlinks[position]:
            errors.append(
                f"The order of the version headers does not match your hyperlinks. "
                f"Found '{versions_from_hyperlinks[position]}' in hyperlinks but expected '{version}'"
            )

    # Ensure the release dates are in descending order
    for position, date in enumerate(dates_from_headers):
        if position == len(dates_from_headers) - 1:
            break

        if date < dates_from_headers[position + 1]:
            errors.append(f"Header with date '{date}' should be listed before '{dates_from_headers[position + 1]}'")

    # Check if the user is using something other than <Added||Changed||Deprecated||Removed||Fixed||Security>
    section_headers = re.findall(SECTION_HEADER_RE, changelog)
    for header in section_headers:
        if header not in {"Added", "Changed", "Deprecated", "Removed", "Fixed", "Security"}:
            errors.append(f"Using non-standard section header '{header}'")

    # Check the order of the sections
    # Simplify the changelog into a list of `##` and `###` headers
    changelog_header_lines = [line for line in changelog.split("\n") if line.startswith(("###", "##"))]
    order = ["### Added", "### Changed", "### Deprecated", "### Removed", "### Fixed", "### Security"]
    current_position_in_order = -1
    version_header = "UNKNOWN"
    for _line in changelog_header_lines:
        line = _line.strip()
        # Reset current position if we are at a version header
        if line.startswith("## "):
            version_header = line
            current_position_in_order = -1

        # Check if the current section is in the correct order
        if line in order:
            section_position = order.index(line)
            if section_position < current_position_in_order:
                errors.append(
                    f"Section '{line}' is out of order in version '{version_header}'. "
                    "Expected section order: [Added, Changed, Deprecated, Removed, Fixed, Security]"
                )
            # Additional check for duplicate sections
            if section_position == current_position_in_order:
                errors.append(f"Duplicate section '{line}' found in version '{version_header}'.")
            current_position_in_order = section_position

    # Find sections with missing bullet points
    changelog_header_and_bullet_lines = [
        line for line in changelog.split("\n") if line.startswith(("### ", "## ", "-"))
    ]
    current_version = "UNKNOWN"
    for position, line in enumerate(changelog_header_and_bullet_lines):
        if line.startswith("## "):
            current_version = line
        # If it's an h3 header, report an error if the next line is not a bullet point, or if there is no next line
        if line.startswith("### ") and (
            position + 1 == len(changelog_header_and_bullet_lines)
            or not changelog_header_and_bullet_lines[position + 1].startswith("-")
        ):
            errors.append(f"Section '{line}' in version '{current_version}' is missing bullet points")

    return errors


if __name__ == "__main__":
    if len(sys.argv) == 2:
        validate_changelog(sys.argv[1])
    if len(sys.argv) > 2:
        print("Usage: python validate_changelog.py [changelog_path]")
        sys.exit(1)

    errors = validate_changelog()
    if errors:
        print("Changelog has formatting errors!")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)

    print("Changelog is valid!")
    sys.exit(0)
