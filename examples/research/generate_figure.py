"""Build a small figure and record its exact inputs."""

import csv
import json
from pathlib import Path
from statistics import mean

from editcheck.provenance import fingerprint


def main():
    root = Path(__file__).resolve().parent
    data = root / 'measurements.csv'
    with data.open(encoding='utf-8', newline='') as stream:
        values = [float(row['minutes']) for row in csv.DictReader(stream)]
    average = mean(values)
    bars = ''.join(
        f'<rect x="{40 + index * 90}" y="{154 - value * 4:g}" width="44" height="{value * 4:g}" fill="#31846d"/>'
        for index, value in enumerate(values)
    )
    figure = root / 'figure.svg'
    figure.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="330" height="210" viewBox="0 0 330 210" role="img">\n'
        '<title>Three illustrative measurements in minutes</title>\n'
        '<rect width="330" height="210" fill="#f2f6f3"/><path d="M24 154H306" stroke="#31473e"/>\n'
        + bars + f'\n<text x="24" y="185" fill="#22352c" font-size="16">Mean: {average:.1f} min</text>\n</svg>\n',
        encoding='utf-8', newline='\n',
    )

    def entry(path):
        return {'path': path.name, 'sha256': fingerprint(path)}

    manifest = {'schema_version': 1, 'figures': [{
        'name': 'Example methods figure', 'artifact': entry(figure),
        'script': entry(Path(__file__)), 'inputs': [entry(data)],
    }]}
    (root / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8', newline='\n')


if __name__ == '__main__':
    main()
