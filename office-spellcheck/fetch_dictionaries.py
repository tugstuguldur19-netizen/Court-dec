"""Download the Mongolian and English Hunspell dictionaries into ./dictionaries.

Run this once, on a computer with internet access, before running from source
or building the Windows app. After that the spellchecker never goes online.

The files come unmodified from the LibreOffice dictionaries repository, pinned
to one commit and checked against known SHA-256 hashes:

  mn_MN  Batmunkh Dorjgotov, LaTeX Project Public License 1.3 (redistributed
         unmodified, together with its README, as that licence requires)
  en_US  SCOWL / Kevin Atkinson et al., permissive licence (see README_en_US.txt)
"""

import hashlib
import os
import sys
import urllib.request

COMMIT = "32b006a2c22a4ac7e8ed3f03346f7b3d85a970a4"
BASE = "https://raw.githubusercontent.com/LibreOffice/dictionaries/" + COMMIT + "/"

FILES = {
    "mn_MN/mn_MN.aff": "042c47f606cf9448b4a57607aedb343860c614212afe4cdb0bd91601fc6d4a4f",
    "mn_MN/mn_MN.dic": "acf71f26468b68d3fd3254e7354032b3cd0603ed5db1fa93bffe144eb73439bb",
    "mn_MN/README_mn_MN.txt": "c1693e062fac02e0585d84fc72df520e6ec01f9783f41d6bde4cd9e9cbe93da0",
    "en/en_US.aff": "e746c882dd6f303c2c46e7452804b9201115a6942cfeb15f18f8edf774d2e24e",
    "en/en_US.dic": "f0b1a234bd178bdd01875b2a392a9647f888b8fe879f79c52aae62c2759b3647",
    "en/README_en_US.txt": "168b4c01cb841f766a72f310b065c04d09cff46376c37a81d799593ce751c371",
}

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(HERE, "dictionaries")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    os.makedirs(TARGET, exist_ok=True)
    for remote, digest in FILES.items():
        dest = os.path.join(TARGET, os.path.basename(remote))
        if os.path.isfile(dest) and sha256(dest) == digest:
            print("ok      ", os.path.basename(dest))
            continue
        print("download", os.path.basename(dest))
        tmp = dest + ".part"
        with urllib.request.urlopen(BASE + remote, timeout=120) as r, open(tmp, "wb") as f:
            while True:
                chunk = r.read(1 << 20)
                if not chunk:
                    break
                f.write(chunk)
        got = sha256(tmp)
        if got != digest:
            os.remove(tmp)
            sys.exit("checksum mismatch for %s: %s" % (remote, got))
        os.replace(tmp, dest)
    print("Dictionaries are in", TARGET)


if __name__ == "__main__":
    main()
