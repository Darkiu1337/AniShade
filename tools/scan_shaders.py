import collections
import re
from pathlib import Path

files = sorted(Path('vendor/anime4k').glob('Anime4K_Restore*.glsl')) + [
    Path('vendor/anime4k/Anime4K_Denoise_Bilateral_Median.glsl'),
    Path('vendor/anime4k/Anime4K_Denoise_Bilateral_Mean.glsl'),
    Path('vendor/anime4k/Anime4K_Denoise_Bilateral_Mode.glsl'),
    Path('vendor/anime4k/Anime4K_Clamp_Highlights.glsl'),
]
funcs = collections.Counter()
directives = collections.Counter()
defines = set()
specials = set()
loops = 0
branches = 0
types = set()

for f in files:
    text = f.read_text(encoding='utf-8')
    for line in text.splitlines():
        s = line.strip()
        if s.startswith('//!'):
            key = s[3:].split()[0] if len(s) > 3 else ''
            directives[key] += 1
        if s.startswith('#define'):
            defines.add(s)
        for m in re.finditer(r'\b([a-zA-Z_]\w*)\s*\(', s):
            name = m.group(1)
            if name in ('vec2', 'vec3', 'vec4', 'mat2', 'mat3', 'mat4'):
                types.add(name)
                continue
            if name in ('if', 'for', 'while', 'return', 'switch'):
                continue
            funcs[name] += 1
        for m in re.finditer(r'\b([A-Za-z_]\w*)_(pos|size|pt|texOff|tex)\b', s):
            specials.add(m.group(2))
        if re.search(r'\bfor\s*\(', s):
            loops += 1
        if re.search(r'\bif\s*\(', s):
            branches += 1

print("directives:", dict(directives))
print("types:", sorted(types))
print("specials:", sorted(specials))
print("loops:", loops, "ifs:", branches)
print("functions:", dict(funcs.most_common(80)))
print("defines sample:")
for d in sorted(defines)[:20]:
    print("  ", d)
