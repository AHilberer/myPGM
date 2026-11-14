"""Check that the wheel holds the files myPGM needs at run time (package data is easy to
lose with a pyproject change). Usage: python check_wheel.py dist/*.whl"""
import fnmatch
import sys
import zipfile

REQUIRED = [
    "myPGM/ui/theme.qss",
    "myPGM/resources/fonts/Inter-*.ttf",
    "myPGM/resources/fonts/JetBrainsMono-*.ttf",
    "myPGM/resources/icons/AppIcon256.png",
    "myPGM/resources/icons/ui/*.svg",
    "myPGM/resources/Example_Ruby_1.asc",
    "myPGM/resources/Example_H2.txt",
]

wheels = [a for a in sys.argv[1:] if a.endswith(".whl")]
if len(wheels) != 1:
    sys.exit(f"expected one wheel, got {wheels}")
names = zipfile.ZipFile(wheels[0]).namelist()
missing = [p for p in REQUIRED if not fnmatch.filter(names, p)]
if missing:
    sys.exit(f"missing from {wheels[0]}: {missing}")
print(f"{wheels[0]}: {len(names)} files, all required data present")
