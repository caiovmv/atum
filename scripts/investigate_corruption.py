"""Investigacao de arquivos corrompidos na biblioteca de musica."""
import os
from pathlib import Path
import mutagen

root = Path('/library/music')
flac_magic = b'fLaC'
id3v2_magic = b'ID3'
ogg_magic = b'OggS'
riff_magic = b'RIFF'

results = {
    'valid': [],
    'null_filled': [],
    'wrong_format': [],
    'truncated': [],
    'unreadable': [],
    'no_audio_data': [],
}

all_files = sorted(f for f in root.rglob('*') if f.is_file())
print(f'Total de arquivos encontrados: {len(all_files)}')

for f in all_files:
    ext = f.suffix.lower()
    size = f.stat().st_size

    if size == 0:
        results['truncated'].append((f, 'Arquivo vazio (0 bytes)'))
        continue

    with open(f, 'rb') as fh:
        header = fh.read(min(4096, size))

    if all(b == 0 for b in header[:256]):
        results['null_filled'].append((f, f'{size/1024/1024:.1f} MB de zeros'))
        continue

    is_flac = header[:4] == flac_magic
    is_mp3_id3 = header[:3] == id3v2_magic
    is_mp3_sync = len(header) >= 2 and header[0] == 0xFF and (header[1] & 0xE0) == 0xE0
    is_ogg = header[:4] == ogg_magic
    is_wav = header[:4] == riff_magic
    is_m4a = header[4:8] == b'ftyp' if len(header) >= 8 else False

    format_ok = False
    detected = 'unknown'

    if ext == '.flac' and is_flac:
        format_ok, detected = True, 'FLAC'
    elif ext == '.mp3' and (is_mp3_id3 or is_mp3_sync):
        format_ok, detected = True, 'MP3'
    elif ext == '.ogg' and is_ogg:
        format_ok, detected = True, 'OGG'
    elif ext == '.wav' and is_wav:
        format_ok, detected = True, 'WAV'
    elif ext in ('.m4a', '.mp4') and is_m4a:
        format_ok, detected = True, 'M4A'
    elif ext == '.flac' and not is_flac:
        if is_mp3_id3 or is_mp3_sync:
            detected = 'MP3 (extensao .flac)'
        elif is_ogg:
            detected = 'OGG (extensao .flac)'
        else:
            detected = f'unknown (magic: {header[:4].hex()})'
    elif ext == '.mp3' and not (is_mp3_id3 or is_mp3_sync):
        detected = f'unknown (magic: {header[:4].hex()})'
    else:
        format_ok, detected = True, ext

    if not format_ok:
        results['wrong_format'].append((f, f'Extensao {ext} mas formato real: {detected}'))
        continue

    try:
        audio = mutagen.File(str(f))
        if audio is None:
            results['unreadable'].append((f, 'mutagen retornou None'))
            continue

        if hasattr(audio, 'info') and audio.info:
            duration = getattr(audio.info, 'length', 0)
            if duration is not None and duration <= 0:
                results['no_audio_data'].append((f, 'Duracao zero'))
                continue

        results['valid'].append(f)
    except Exception as e:
        err = str(e)[:100]
        results['unreadable'].append((f, err))

print()
print('=' * 60)
print('RESULTADOS DA INVESTIGACAO')
print('=' * 60)

valid_count = len(results['valid'])
total = len(all_files)
pct = (valid_count / total * 100) if total > 0 else 0
print(f'Validos:              {valid_count} ({pct:.1f}%)')

for cat, label in [
    ('null_filled', 'Preenchidos com null'),
    ('wrong_format', 'Formato errado'),
    ('truncated', 'Truncados/vazios'),
    ('unreadable', 'Illegiveis (mutagen)'),
    ('no_audio_data', 'Sem dados de audio'),
]:
    count = len(results[cat])
    if count > 0:
        print(f'{label + ":":22s} {count}')

total_bad = total - valid_count
if total_bad > 0:
    total_bad_size = 0
    print()
    for cat, label in [
        ('null_filled', 'PREENCHIDOS COM NULL (lixo)'),
        ('wrong_format', 'FORMATO ERRADO (extensao nao bate com conteudo)'),
        ('truncated', 'TRUNCADOS/VAZIOS'),
        ('unreadable', 'ILLEGIVEIS PELO MUTAGEN'),
        ('no_audio_data', 'SEM DADOS DE AUDIO'),
    ]:
        items = results[cat]
        if not items:
            continue
        print(f'--- {label} ({len(items)}) ---')
        for f_path, reason in items:
            rel = f_path.relative_to(root)
            size_mb = f_path.stat().st_size / 1024 / 1024
            total_bad_size += f_path.stat().st_size
            print(f'  [{size_mb:7.1f} MB] {rel}')
            print(f'             {reason}')
        print()

    print(f'Total corrompido/invalido: {total_bad} arquivos ({total_bad_size/1024/1024:.1f} MB)')
else:
    print()
    print('Nenhum arquivo corrompido encontrado!')

# Also check for duplicate track numbers in same album
print()
print('=' * 60)
print('VERIFICACAO DE DUPLICATAS')
print('=' * 60)
from collections import defaultdict
albums = defaultdict(list)
for f in results['valid']:
    albums[f.parent].append(f.name)

dupes_found = 0
for album_path, files in sorted(albums.items()):
    import re
    track_nums = defaultdict(list)
    for fname in files:
        m = re.match(r'^(\d+)\s*[-.]', fname)
        if m:
            track_nums[m.group(1)].append(fname)
    for num, fnames in track_nums.items():
        if len(fnames) > 1:
            if dupes_found == 0:
                print('Tracks duplicados no mesmo album:')
            dupes_found += 1
            rel = album_path.relative_to(root)
            print(f'  {rel}/ -> Track {num}: {len(fnames)} arquivos')
            for fn in fnames:
                print(f'    - {fn}')

if dupes_found == 0:
    print('Nenhuma duplicata encontrada.')
