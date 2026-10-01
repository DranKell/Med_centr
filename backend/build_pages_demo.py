"""Build a read-only GitHub Pages demo from the bundled draft SOP catalogue."""

import json
import shutil
import sys
from pathlib import Path

from sop_catalog import CATALOGUE, build_sop


ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / 'frontend' / 'pages-demo'


def build(output: Path) -> int:
    output.mkdir(parents=True, exist_ok=True)
    shutil.copytree(SOURCE, output, dirs_exist_ok=True)

    sops = []
    for index, (category, key, title) in enumerate(CATALOGUE, start=1):
        sop = build_sop(category, title, key)
        sop['id'] = index
        sop['number'] = str(index)
        sop['status'] = 'draft'
        sop['approval_order'] = None
        sop['normative_refs'] = (
            'В этом демонстрационном проекте нормативные ссылки не подтверждены. '
            'Проверьте применимость, актуальность и точные пункты по официальным источникам '
            'до использования или утверждения документа.'
        )
        sops.append(sop)

    (output / 'sops.json').write_text(
        json.dumps(sops, ensure_ascii=False, indent=2) + '\n', encoding='utf-8'
    )
    (output / '.nojekyll').touch()
    return len(sops)


if __name__ == '__main__':
    destination = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / '_site'
    print(f'Built {build(destination)} read-only SOP examples in {destination}')