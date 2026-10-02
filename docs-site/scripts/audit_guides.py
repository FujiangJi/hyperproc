"""Check maintained examples against source signatures without importing hyperproc."""
import ast
import inspect
from pathlib import Path
import re
import tomllib

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
CURATED_TUTORIALS = {'aviris3-walkthrough.md', 'caveats.md', 'pace-tutorial.md'}


def maintained_pages():
    return [p for p in sorted((ROOT/'docs').rglob('*.md'))
            if 'api' not in p.relative_to(ROOT/'docs').parts
            and ('tutorials' not in p.relative_to(ROOT/'docs').parts
                 or p.name in CURATED_TUTORIALS)]


def source_interfaces():
    aliases, functions, classes = {}, {}, set()
    for path in (REPO/'hyperproc').rglob('*.py'):
        if path.name.startswith('._'):
            continue
        module = '.'.join(path.relative_to(REPO).with_suffix('').parts)
        if module.endswith('.__init__'):
            module = module[:-9]
        tree = ast.parse(path.read_text())
        for node in tree.body:
            if isinstance(node, ast.ImportFrom) and node.module and not node.level:
                for name in node.names:
                    aliases[module+'.'+(name.asname or name.name)] = node.module+'.'+name.name
            elif isinstance(node, ast.Assign) and isinstance(node.value, ast.Name):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        aliases[module+'.'+target.id] = module+'.'+node.value.id
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions[module+'.'+node.name] = node.args
            elif isinstance(node, ast.ClassDef):
                classes.add(module+'.'+node.name)
    return aliases, functions, classes


def resolve(name, aliases):
    seen = set()
    while name in aliases and name not in seen:
        seen.add(name)
        name = aliases[name]
    return name


def signature(arguments):
    parameters = []
    positional = arguments.posonlyargs + arguments.args
    required = len(positional) - len(arguments.defaults)
    for i, arg in enumerate(positional):
        kind = inspect.Parameter.POSITIONAL_ONLY if i < len(arguments.posonlyargs) else inspect.Parameter.POSITIONAL_OR_KEYWORD
        default = inspect.Parameter.empty if i < required else None
        parameters.append(inspect.Parameter(arg.arg, kind, default=default))
    if arguments.vararg:
        parameters.append(inspect.Parameter(arguments.vararg.arg, inspect.Parameter.VAR_POSITIONAL))
    for arg, default in zip(arguments.kwonlyargs, arguments.kw_defaults):
        parameters.append(inspect.Parameter(arg.arg, inspect.Parameter.KEYWORD_ONLY,
                          default=inspect.Parameter.empty if default is None else None))
    if arguments.kwarg:
        parameters.append(inspect.Parameter(arguments.kwarg.arg, inspect.Parameter.VAR_KEYWORD))
    return inspect.Signature(parameters)


def audit():
    aliases, functions, classes = source_interfaces()
    extras = tomllib.loads((REPO/'pyproject.toml').read_text())['project']['optional-dependencies']
    errors, blocks, calls = [], 0, 0
    pages = maintained_pages()
    for path in pages:
        text = path.read_text()
        for group in re.findall(r"hyperproc\[([a-z0-9,-]+)\]", text):
            for extra in group.split(','):
                if extra not in extras:
                    errors.append(f'{path.relative_to(ROOT)}: unknown install extra {extra}')
        imports = {'hp':'hyperproc', 'hc':'hyperproc.correct'}
        for index, code in enumerate(re.findall(r'```python[^\n]*\n(.*?)\n```', text, re.S), 1):
            blocks += 1
            try:
                tree = ast.parse(code)
            except SyntaxError as exc:
                errors.append(f'{path.relative_to(ROOT)}: Python block {index}: {exc}')
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for name in node.names:
                        imports[name.asname or name.name.split('.')[0]] = name.name if name.asname else name.name.split('.')[0]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    for name in node.names:
                        imports[name.asname or name.name] = node.module+'.'+name.name
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                name = ast.unparse(node.func)
                first, separator, rest = name.partition('.')
                if first not in imports or not imports[first].startswith('hyperproc'):
                    continue
                qualified = imports[first] + (separator+rest if separator else '')
                target = resolve(qualified, aliases)
                if target not in functions:
                    # Lazy exports are unique definitions in child modules.
                    candidates = [name for name in functions if name.startswith(target.rsplit('.',1)[0]+'.')
                                  and name.endswith('.'+target.rsplit('.',1)[-1])]
                    if len(candidates) == 1:
                        target = candidates[0]
                    elif target in classes:
                        continue
                    else:
                        errors.append(f'{path.relative_to(ROOT)}: Python block {index}: callable not found in source: {qualified}')
                        continue
                if any(isinstance(arg, ast.Starred) for arg in node.args) or any(key.arg is None for key in node.keywords):
                    continue
                calls += 1
                try:
                    signature(functions[target]).bind(*[None for _ in node.args],
                                                      **{key.arg:None for key in node.keywords})
                except TypeError as exc:
                    errors.append(f'{path.relative_to(ROOT)}: Python block {index}, line {node.lineno}: {qualified}: {exc}')
    return errors, {'pages':len(pages), 'python_blocks':blocks, 'source_bound_calls':calls}


if __name__ == '__main__':
    errors, counts = audit()
    if errors:
        raise SystemExit('\n'.join(errors))
    print(f'PASS: maintained guide audit {counts}')
