import os
import re

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC_ROOT = os.path.join(ROOT, "src", "povichain")


FORBIDDEN_PATTERNS = (
    re.compile(r"\bimport\s+random\b"),
    re.compile(r"\bfrom\s+random\s+import\b"),
    re.compile(r"\bnumpy\.random\b"),
    re.compile(r"\bnp\.random\b"),
    re.compile(r"\brandn\s*\("),
    re.compile(r"\brandom\.(gauss|normalvariate|random|uniform|randint|choice|sample|shuffle)\b"),
    re.compile(r"\bgauss\s*\("),
    re.compile(r"\bnormalvariate\s*\("),
)


def _iter_source_files():
    for dirpath, _dirs, files in os.walk(SRC_ROOT):
        for fn in files:
            if fn.endswith(".py"):
                yield os.path.join(dirpath, fn)


def test_no_random_or_gaussian_in_source():
    offenders = []
    for path in _iter_source_files():
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        for pat in FORBIDDEN_PATTERNS:
            if pat.search(text):
                offenders.append((path, pat.pattern))
    assert not offenders, "forbidden_random_or_gauss_found:" + str(offenders)
