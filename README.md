# Socle

Socle is a cross-platform desktop application for working with developer and data workflows in one place. It focuses on a practical editor-and-grid experience for inspecting data, running queries, browsing metadata, and handling related utility tasks from a single UI.

## What Socle Is For

Socle is designed for users who need a fast desktop tool for everyday technical work such as:

- browsing and inspecting structured data
- editing and running commands or queries
- exploring metadata and related objects
- exporting results and working with supporting utilities
- using the same application across Windows and macOS

## Main Areas

Depending on the enabled providers and features in the build, Socle can include:

- command editors with rich tooling
- result grids for viewing and editing data
- object and metadata exploration
- import and export support
- built-in update workflow

## Platforms

Current release artifacts are prepared for:

- Windows x64
- macOS arm64

## Getting Started

1. Download the ZIP file for your platform.
2. Extract it to a writable folder.
3. Launch the included Socle application executable.

Platform-specific quick-start notes are available in `README.txt` inside the release package.

## Updates

Socle includes an update workflow based on the published release manifest and bundled updater.

## macOS release workflow maintenance

The signing workflow normalizes the complete app payload before signing. All
non-Mach-O files in `Contents/MacOS`, including icons, third-party licenses,
managed DLLs and Copilot resources, move to `Contents/Resources`. Relative
symlinks preserve their original paths. Licenses are retained. Embedded apps
move to `Contents/Frameworks`, keeping any inner bundles intact.

Native libraries and helper binaries are signed before enclosing app bundles,
from the deepest bundle outward. The outer Socle app is signed last and verified
before notarization. The workflow can reprocess existing `.zip.temp` assets;
changing this layout step does not require a new application build.

Run the layout regression tests with `python3 tests/test_macos_bundle_layout.py`
and `file` available on PATH. These exercise the actual workflow script,
including the Octicons license, runtime preloads, nested apps and destination
conflicts. Actual Developer ID signing and notarization run on GitHub macOS.

## Support

Public release information:

- https://github.com/socleappsupp/socle-release 
