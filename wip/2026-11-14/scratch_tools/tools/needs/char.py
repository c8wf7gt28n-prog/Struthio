import json, sys, os
root = sys.argv[1]
man = json.load(open(os.path.join(root, 'MANIFEST.json'), encoding='utf-8'))['files']
c = json.load(open(os.path.join(root, 'branding/stacy/character.json'), encoding='utf-8'))
for name, meta in c.get('files', {}).items():
    k = 'branding/stacy/' + name
    print(name, meta.get('bytes'), 'IN MANIFEST' if k in man else 'ABSENT from manifest')
print('design_authority', c.get('design_authority'), 'branding/arcfairy/ART_DIRECTION.md' in man)
print({k: v for k, v in c.items() if k not in ('files', 'invariants')})
