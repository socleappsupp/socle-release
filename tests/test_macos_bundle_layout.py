"""Exercise the actual workflow's relocation script without Apple credentials.

Run with Python 3 and the `file` command available on PATH. macOS signing and
notarization still require the GitHub macOS runner.
"""
from contextlib import contextmanager
import os
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import textwrap
import unittest

WORKFLOW = Path(__file__).resolve().parents[1] / ".github/workflows/sign-existing-macos-release.yml"
TEXT = WORKFLOW.read_text(encoding="utf-8")
STEP = TEXT.split("      - name: Place all application resources outside MacOS\n", 1)[1].split("      - name: Create entitlements", 1)[0]
SCRIPT = textwrap.dedent(STEP.split("/usr/bin/python3 <<'PY'\n", 1)[1].rsplit("          PY", 1)[0])
MACHO = struct.pack("<IIIIIIII", 0xFEEDFACF, 0x0100000C, 0, 2, 0, 0, 0, 0)


@contextmanager
def fixture():
    with tempfile.TemporaryDirectory(prefix="socle-layout-") as folder:
        previous = Path.cwd()
        os.chdir(folder)
        try:
            root = Path("Socle.app/Contents")
            (root / "MacOS").mkdir(parents=True)
            yield root
        finally:
            os.chdir(previous)


def write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def relocate():
    exec(compile(SCRIPT, str(WORKFLOW), "exec"), {})


class BundleLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which("file"):
            raise RuntimeError("The file command must be available on PATH.")
        with tempfile.TemporaryDirectory() as folder:
            path = write(Path(folder) / "macho", MACHO)
            if "Mach-O" not in subprocess.check_output(["file", "-b", str(path)], text=True):
                raise RuntimeError("The file command did not recognize the Mach-O fixture.")

    def test_assets_and_root_data_without_copilot_runtime(self):
        with fixture() as root:
            macos = root / "MacOS"
            executable = write(macos / "Socle", MACHO)
            license_file = write(macos / "Assets/Icons/ThirdParty/Octicons/LICENSE.txt", b"Keep this license.\n")
            readme = write(macos / "README.txt", b"Installation instructions")
            relocate()
            self.assertFalse(executable.is_symlink())
            for path in (license_file, readme):
                target = root / "Resources" / path.relative_to(macos)
                self.assertTrue(path.is_symlink())
                self.assertEqual(path.read_bytes(), target.read_bytes())
                self.assertTrue(path.resolve().is_relative_to(root.resolve()))
            self.assertEqual(license_file.read_bytes(), b"Keep this license.\n")
            relocate()  # Already normalized input must remain usable.
            self.assertEqual(readme.read_bytes(), b"Installation instructions")

    def test_mixed_runtime_and_nested_apps_keep_paths(self):
        with fixture() as root:
            macos = root / "MacOS"
            runtime = macos / "runtimes/osx-arm64/native"
            originals = {
                "Socle": MACHO,
                "Socle-updater": MACHO,
                "libSkiaSharp.dylib": MACHO,
                "runtimes/osx-arm64/native/runtime.node": MACHO,
                "runtimes/osx-arm64/native/preloads/extension_bootstrap.mjs": b"export {};",
                "runtimes/osx-arm64/native/package.json": b"{}",
                "Assets/Icons/ThirdParty/Octicons/LICENSE.txt": b"License text",
            }
            for name, data in originals.items():
                write(macos / name, data)
            app = runtime / "plugins/computer-use/Copilot Computer Use.app"
            write(app / "Contents/MacOS/helper", MACHO)
            write(app / "Contents/Info.plist", b"<plist/>")
            write(app / "Contents/Frameworks/Inner.app/Contents/MacOS/inner", MACHO)
            relocate()
            for name, data in originals.items():
                original = macos / name
                self.assertEqual(original.read_bytes(), data)
                self.assertEqual(original.is_symlink(), data != MACHO)
            self.assertTrue(app.is_symlink())
            relocated = root / "Frameworks/Copilot Computer Use.app"
            self.assertEqual((app / "Contents/MacOS/helper").read_bytes(), MACHO)
            self.assertFalse((relocated / "Contents/Info.plist").is_symlink())
            self.assertTrue((relocated / "Contents/Frameworks/Inner.app").is_dir())
            self.assertFalse((root / "Frameworks/Inner.app").exists())
            relocate()
            self.assertEqual((app / "Contents/Frameworks/Inner.app/Contents/MacOS/inner").read_bytes(), MACHO)

    def test_conflicting_resource_is_never_overwritten(self):
        with fixture() as root:
            original = write(root / "MacOS/Assets/LICENSE.txt", b"original")
            target = write(root / "Resources/Assets/LICENSE.txt", b"existing")
            with self.assertRaisesRegex(RuntimeError, "destination already exists"):
                relocate()
            self.assertEqual(original.read_bytes(), b"original")
            self.assertEqual(target.read_bytes(), b"existing")

    def test_signing_orders_helpers_before_enclosing_bundles(self):
        self.assertLess(TEXT.index('echo "Signing executable Mach-O files..."'), TEXT.index('echo "Signing nested app bundles..."'))
        self.assertLess(TEXT.index('echo "Signing nested app bundles..."'), TEXT.index('echo "Signing app bundle..."'))
        self.assertIn('find Socle.app/Contents -depth -type d -name "*.app"', TEXT)
        self.assertIn('! -path "Socle.app/Contents/MacOS/Socle"', TEXT)
        self.assertIn('codesign --verify --deep --strict', TEXT)


if __name__ == "__main__":
    unittest.main()
