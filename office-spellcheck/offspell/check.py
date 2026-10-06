"""Running the speller over a source."""


def find_hits(speller, units, progress=None, cancelled=None):
    """Check every unit's text. Pure computation, so it can run on a worker
    thread while the window stays responsive. Returns one hit list per unit."""
    results = []
    total = len(units)
    for i, unit in enumerate(units):
        if cancelled and cancelled():
            break
        results.append(speller.misspellings(unit.text))
        if progress and (i % 50 == 0 or i == total - 1):
            progress(i + 1, total)
    return results


def build_issues(source, units, results):
    issues = []
    for unit, hits in zip(units, results):
        if hits:
            issues += source.make_issues(unit, hits)
    return issues


def scan(source, speller, progress=None):
    units = source.units()
    return build_issues(source, units, find_hits(speller, units, progress))
