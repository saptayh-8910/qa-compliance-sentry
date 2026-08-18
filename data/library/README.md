# Public document library

This directory contains version-pinned, publicly reusable sources used for
real-data retrieval testing. `catalog.json` records each source URL, release,
checksum, retrieval date, attribution, and license.

## OWASP ASVS 5.0.0

The unmodified English JSON release of the OWASP Application Security
Verification Standard 5.0.0 is included under the Creative Commons
Attribution-ShareAlike 4.0 International license. It was retrieved from the
official OWASP/ASVS repository at the stable `v5.0.0_release` tag.

- Project: https://github.com/OWASP/ASVS
- Stable release: https://github.com/OWASP/ASVS/releases/tag/v5.0.0_release
- License: https://creativecommons.org/licenses/by-sa/4.0/
- Local transformation: the application converts the structured JSON into one
  searchable Markdown-style section per requirement at runtime. The source JSON
  itself is unchanged.

OWASP and the OWASP logo are trademarks of the OWASP Foundation. Inclusion in
this learning project does not imply OWASP endorsement.
