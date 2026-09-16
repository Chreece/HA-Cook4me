#!/usr/bin/env python3
from pathlib import Path

path = Path(__file__).with_name('apply_semantic_standalone_closure_patch_v60.py')
text = path.read_text(encoding='utf-8')
label = '        "pass standalone payload",\n    )\n'
label_at = text.find(label)
if label_at < 0:
    raise SystemExit('pass standalone payload block not found')
start = text.rfind('    text = replace_once(\n', 0, label_at)
if start < 0:
    raise SystemExit('replace_once block start not found')
end = label_at + len(label)
replacement = '''    text = replace_once(
        text,
        "    return compile_semantic_concepts(\\n        payloads,\\n        confirmation_payload=confirmation_payload,\\n        confirmation_file=confirmation_file,\\n        syntax_confirmation_ids=syntax_confirmation_ids,\\n        syntax_confirmation_file=syntax_confirmation_file,\\n    )\\n",
        "    return compile_semantic_concepts(\\n        payloads,\\n        confirmation_payload=confirmation_payload,\\n        confirmation_file=confirmation_file,\\n        syntax_confirmation_ids=syntax_confirmation_ids,\\n        syntax_confirmation_file=syntax_confirmation_file,\\n        standalone_payload=standalone_payload,\\n        standalone_file=standalone_file,\\n    )\\n",
        "pass standalone payload",
    )
'''
path.write_text(text[:start] + replacement + text[end:], encoding='utf-8')
