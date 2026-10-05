#!/usr/bin/env python3
"""Inspect installed hyperproc source or a selected runtime callable; no installs."""
from __future__ import annotations
import argparse
import ast
import importlib
import importlib.metadata as md
import importlib.util
import inspect
import json
from pathlib import Path


def installed_source():
    spec = importlib.util.find_spec('hyperproc')
    if not spec or not spec.origin:
        raise RuntimeError('hyperproc source is not discoverable in this interpreter.')
    root = Path(spec.origin).parent
    try:
        version = md.version('hyperproc')
    except md.PackageNotFoundError:
        version = 'distribution metadata unavailable'
    modules, declarations, aliases = {}, {}, {}
    for path in sorted(root.rglob('*.py')):
        parts = list(path.relative_to(root.parent).with_suffix('').parts)
        if parts[-1] == '__init__':
            parts.pop()
        module = '.'.join(parts)
        tree = ast.parse(path.read_text())
        exports, constants = [], []
        for node in tree.body:
            if isinstance(node, ast.ImportFrom) and (node.module or '').startswith('hyperproc') and not node.level:
                for item in node.names:
                    aliases[module+'.'+(item.asname or item.name)] = node.module+'.'+item.name
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                for target in targets:
                    if isinstance(target, ast.Name) and target.id == '__all__':
                        try:
                            exports = ast.literal_eval(node.value)
                        except (ValueError, TypeError):
                            pass
                    elif isinstance(target, ast.Name) and node.value is not None:
                        if isinstance(node.value, ast.Name):
                            aliases[module+'.'+target.id] = module+'.'+node.value.id
                        if target.id.isupper():
                            constants.append(target.id)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                declarations[module+'.'+node.name] = declaration(node, module+'.'+node.name, module, path)
                if isinstance(node, ast.ClassDef):
                    for member in node.body:
                        if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            q = module+'.'+node.name+'.'+member.name
                            declarations[q] = declaration(member, q, module, path)
        modules[module] = {'path': str(path), 'exports': exports, 'constants': constants}
    return version, modules, declarations, aliases


def declaration(node, qualified, module, path):
    if isinstance(node, ast.ClassDef):
        signature = 'class '+node.name+'('+', '.join(ast.unparse(b) for b in node.bases)+')'
    else:
        signature = ('async ' if isinstance(node, ast.AsyncFunctionDef) else '')+'def '+node.name+'('+ast.unparse(node.args)+')'
        if node.returns:
            signature += ' -> '+ast.unparse(node.returns)
    return {'qualified_name': qualified, 'module': module, 'source': str(path), 'line': node.lineno, 'signature': signature, 'docstring': ast.get_docstring(node), 'kind': 'class' if isinstance(node, ast.ClassDef) else 'callable'}


def resolve_source(name, declarations, aliases):
    seen = set()
    while name not in seen:
        seen.add(name)
        if name in declarations:
            return declarations[name]
        replacement = None
        for prefix in sorted(aliases, key=len, reverse=True):
            if name == prefix or name.startswith(prefix+'.'):
                replacement = aliases[prefix]+name[len(prefix):]
                break
        if not replacement:
            break
        name = replacement
    return None


def runtime_symbol(name):
    if not name.startswith('hyperproc.'):
        raise ValueError('Only fully qualified hyperproc symbols are supported.')
    parts = name.split('.')
    for split in range(len(parts)-1, 0, -1):
        module_name = '.'.join(parts[:split])
        try:
            obj = importlib.import_module(module_name)
        except ModuleNotFoundError as exc:
            if exc.name and (module_name == exc.name or module_name.startswith(exc.name+'.')):
                continue
            raise
        for field in parts[split:]:
            obj = getattr(obj, field)
        if not callable(obj):
            raise TypeError('Requested runtime symbol is not callable; inspect its module/constants in source mode.')
        return {'qualified_name': name, 'signature': str(inspect.signature(obj)), 'docstring': inspect.getdoc(obj), 'resolved_module': getattr(obj, '__module__', None)}
    raise LookupError('Cannot resolve requested runtime symbol.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--list-modules', action='store_true')
    parser.add_argument('--module', help='Exact installed module; list declarations without importing it.')
    parser.add_argument('--symbol', help='Fully qualified name or export alias.')
    parser.add_argument('--runtime', action='store_true', help='Import only the requested symbol and inspect its real signature.')
    parser.add_argument('--doc', action='store_true', help='Include complete docstring for the requested symbol.')
    args = parser.parse_args()
    if args.runtime and not args.symbol:
        parser.error('--runtime requires --symbol')
    try:
        version, modules, declarations, aliases = installed_source()
        result = {'installed_version': version, 'baseline': '0.1.2', 'scope': 'Installed source/signatures follow current code; scientific guidance needs review after behavior changes.'}
        if args.symbol:
            found = runtime_symbol(args.symbol) if args.runtime else resolve_source(args.symbol, declarations, aliases)
            if not found:
                raise LookupError('Symbol not found statically; a lazy/dynamic export may require --runtime.')
            result['symbol'] = {k:v for k,v in found.items() if args.doc or k != 'docstring'}
        elif args.module:
            if args.module not in modules:
                raise LookupError('Module not present in installed source.')
            result['module'] = modules[args.module]
            result['declarations'] = [{k:v for k,v in row.items() if k != 'docstring'} for row in declarations.values() if row['module']==args.module]
        else:
            result['modules'] = list(modules)
            result['source_declaration_count'] = len(declarations)
            result['usage'] = 'Choose --module or --symbol for bounded detail; --runtime --doc verifies a specific installed callable.'
        print(json.dumps(result, indent=2))
        return 0
    except Exception as exc:
        # Do not dump a provider/configuration exception containing secrets.
        print(json.dumps({'status': 'unavailable', 'error_type': type(exc).__name__, 'action': 'Check the active interpreter, requested name and optional dependencies. Use source mode if runtime imports are unavailable.'}, indent=2))
        return 2

if __name__ == '__main__':
    raise SystemExit(main())
