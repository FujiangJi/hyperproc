#!/usr/bin/env python3
"""Check small-file skill references, complete source coverage and optional runtime tests."""
from __future__ import annotations
import argparse
import ast
import hashlib
import json
import re
from pathlib import Path

BUNDLE=Path(__file__).resolve().parents[1]


def require(condition,message):
    if not condition:
        raise AssertionError(message)


def inventory_records():
    index=json.loads((BUNDLE/'references/provenance/api-inventory.json').read_text())
    root=BUNDLE/'references/provenance'
    return index,[json.loads((root/r['record']).read_text()) for r in index['module_records']]


def signature(node):
    return ('async ' if isinstance(node,ast.AsyncFunctionDef) else '')+'def '+node.name+'('+ast.unparse(node.args)+')'+(' -> '+ast.unparse(node.returns) if node.returns else '')


def integrity(source_root=None):
    index,modules=inventory_records();counts={'modules':len(modules),'functions':0,'classes':0,'class_members':0}
    seen=set();verified=0
    for m in modules:
        require((BUNDLE/'references'/m['reference']).is_file(),'Missing module index')
        counts['classes']+=len(m['classes'])
        for row in m['symbols']+m['classes']:
            name=row['qualified_name'];require(name not in seen,'Duplicate symbol: '+name);seen.add(name)
            doc=BUNDLE/'references'/row['reference'];require(doc.is_file(),'Missing symbol: '+name)
            require(name in doc.read_text(),'Wrong symbol document')
            if row.get('kind')=='function':counts['functions']+=1
            elif row.get('kind')=='member':counts['class_members']+=1
        for c in m['constants']:
            require((BUNDLE/'references'/c['reference']).is_file(),'Missing constant expression')
        if source_root:
            path=source_root/m['source_path']
            require(hashlib.sha256(path.read_bytes()).hexdigest()==m['sha256'],'Source hash differs: '+m['module'])
            tree=ast.parse(path.read_text());actual={};classes=set()
            for node in tree.body:
                if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):
                    actual[m['module']+'.'+node.name]=signature(node)
                if isinstance(node,ast.ClassDef):
                    q=m['module']+'.'+node.name;classes.add(q)
                    for member in node.body:
                        if isinstance(member,(ast.FunctionDef,ast.AsyncFunctionDef)):
                            actual[q+'.'+member.name]=signature(member)
            require(set(actual)=={r['qualified_name'] for r in m['symbols']},'Missing declarations: '+m['module'])
            require(classes=={r['qualified_name'] for r in m['classes']},'Missing classes: '+m['module'])
            for r in m['symbols']:
                require(actual[r['qualified_name']] in (BUNDLE/'references'/r['reference']).read_text(),'Signature differs: '+r['qualified_name'])
            verified+=1
    require(counts==index['coverage'],'Coverage counts differ')
    if source_root:
        actual_paths={str(p.relative_to(source_root)) for p in (source_root/'hyperproc').rglob('*.py')}
        require(actual_paths=={m['source_path'] for m in modules},'Module set incomplete')
    links=0;max_words=0;max_doc=None
    for path in BUNDLE.rglob('*.md'):
        body=path.read_text();words=len(body.split())
        if words>max_words:max_words,max_doc=words,str(path.relative_to(BUNDLE))
        require(words<=900,'Instruction/reference exceeds 900 words: '+str(path))
        for target in re.findall(r'\[[^\]]*\]\(([^\s)]+)\)',body):
            if target.startswith(('https:','http:','mailto:','#')):continue
            require((path.parent/target.split('#')[0]).exists(),'Broken link: '+str(path)+' → '+target);links+=1
    scripts=list((BUNDLE/'scripts').glob('*.py'))
    for script in scripts:ast.parse(script.read_text(),filename=str(script))
    return {'coverage':counts,'source_modules_verified':verified,'local_links_checked':links,'scripts_parsed':len(scripts),'largest_markdown_words':max_words,'largest_markdown_file':max_doc,'scope':'Source/reference integrity and small-document granularity, not every algorithm independently validated.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root',type=Path,help='Directory containing reviewed extracted wheel hyperproc/ tree; no download.')
    parser.add_argument('--runtime',action='store_true')
    parser.add_argument('--output',type=Path,help='New result JSON, not overwritten.')
    args=parser.parse_args();report={'integrity':integrity(args.source_root)}
    if args.runtime:
        from validate_runtime import run_checks
        report['runtime']=run_checks(BUNDLE)
    payload=json.dumps(report,indent=2,allow_nan=False)+'\n'
    if args.output:
        with args.output.open('x') as stream:stream.write(payload)
    else:print(payload,end='')
    return 0

if __name__=='__main__':
    raise SystemExit(main())
