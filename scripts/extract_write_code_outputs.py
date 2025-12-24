#!/usr/bin/env python3
import json
import os
from pathlib import Path

SRC = Path('reports/prompt_test_results_full.jsonl')
OUT_ROOT = Path('reports/generated_from_model/full_run')
OUT_ROOT.mkdir(parents=True, exist_ok=True)

written = []
missing = 0
with SRC.open('r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except Exception as e:
            print('JSON parse error:', e)
            continue
        prompt_i = obj.get('i') or obj.get('prompt_index') or 'unknown'
        events = obj.get('events', [])
        for ev in events:
            if ev.get('event') == 'PARSED_TOOL' and ev.get('payload', {}).get('tool') == 'write_code':
                args = ev['payload'].get('args', {})
                orig_fp = args.get('filepath') or 'file.py'
                content = args.get('content', '')
                # sanitize filename
                base = os.path.basename(orig_fp)
                if not base:
                    base = f'file_{len(written)+1}.py'
                dest_dir = OUT_ROOT / f'prompt_{prompt_i}'
                dest_dir.mkdir(parents=True, exist_ok=True)
                dest_path = dest_dir / base
                # if file exists, append a counter
                if dest_path.exists():
                    for k in range(1, 1000):
                        p2 = dest_dir / f"{dest_path.stem}_{k}{dest_path.suffix}"
                        if not p2.exists():
                            dest_path = p2
                            break
                with dest_path.open('w', encoding='utf-8', newline='\n') as out:
                    out.write(content)
                # write metadata
                meta = {
                    'prompt_i': prompt_i,
                    'orig_filepath': orig_fp,
                    'dest': str(dest_path),
                }
                with (dest_path.parent / (dest_path.name + '.meta.json')).open('w', encoding='utf-8') as m:
                    json.dump(meta, m, indent=2)
                written.append(str(dest_path))

print(f'Wrote {len(written)} files to {OUT_ROOT} (skipped {missing})')
for p in written:
    print('-', p)
