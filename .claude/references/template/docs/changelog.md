---
recommended: false
depends_on: [all]
freshness: every-release
diataxis: reference
description: "User-facing changelog format following Keep a Changelog conventions."
designer_description: "When /document generates your user-facing changelog, I'm the template that shapes each release entry into the Keep-a-Changelog buckets (Added, Changed, Deprecated, Removed, Fixed, Security) using your plan's Docs: fields and the real changes from the diff, so your users and downstream integrators can scan one file and know which of their workflows moved, broke, or grew new surface in this version."
---

# TEMPLATE -- CHANGELOG

> **How to use this template:** Create a `CHANGELOG.md` in your project root. Add entries for each release following the format below. Based on [Keep a Changelog](https://keepachangelog.com/).

## Format

```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- {{New feature description}}

### Changed
- {{Change to existing functionality}}

### Deprecated
- {{Feature that will be removed in a future version}}

### Removed
- {{Feature removed in this version}}

### Fixed
- {{Bug fix description}}

### Security
- {{Security vulnerability fix}}

## [{{version}}] -- {{YYYY-MM-DD HH:MM UTC}}

### Added
- {{Feature description}} (#{{issue-number}})
```

## Conventions

- **Newest first**: most recent version at the top
- **[Unreleased]** section: accumulate changes as they are merged, before cutting a release
- **Categories**: use only the 6 categories above (Added, Changed, Deprecated, Removed, Fixed, Security)
- **Link to issues/PRs**: reference issue numbers where applicable
- **Version links**: at the bottom of the file, add comparison links:
  ```
  [Unreleased]: https://github.com/{{org}}/{{repo}}/compare/v{{version}}...HEAD
  [{{version}}]: https://github.com/{{org}}/{{repo}}/compare/v{{prev}}...v{{version}}
  ```

## Freshness Policy

Add entries to the [Unreleased] section as changes are merged. Move entries to a versioned section when cutting a release.
