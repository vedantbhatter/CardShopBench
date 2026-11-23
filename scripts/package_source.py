"""Export a portable source archive without hosting identity, keys, or private runs."""
from pathlib import Path
import zipfile
root=Path(__file__).resolve().parents[1]
with zipfile.ZipFile(root/'dist/source.zip','w',zipfile.ZIP_DEFLATED) as z:
    for p in sorted(root.rglob('*')):
        parts=p.relative_to(root).parts
        if not p.is_file() or any(x in parts for x in ('.git','.openai','.venv','__pycache__','runs')):
            continue
        if p.name in ('.env','source.zip') or p.suffix=='.pyc': continue
        z.write(p,Path('cardshopbench')/p.relative_to(root))
print('Wrote dist/source.zip')
