#!/usr/bin/env python3
"""
n8n Prompts Loader — layered resolution of prompt files.

Prompts are plain markdown files. Resolution order (project overrides plugin):

    1. $N8N_PROMPTS_DIR                       (explicit override)
    2. <cwd>/.n8n-files/prompts               (project-scoped)
    3. <cwd>/prompts                          (project-scoped)
    4. <plugin>/data/prompts                  (plugin library — shared primitives)

The first match wins. Use this to keep project-specific content (voice,
rubrics, brand) out of the plugin repo while still benefiting from shared
primitives shipped with the plugin.

Usage:
    python3 prompts.py --get <key>              # print resolved prompt body
    python3 prompts.py --path <key>             # print resolved file path
    python3 prompts.py --list                   # list all keys across sources
    python3 prompts.py --sources                # show search path (debug)

Keys are filenames without the .md extension. Subdirs become slashes:
    data/prompts/library/judge-rubric.md  ->  library/judge-rubric
"""

import argparse
import io
import os
import sys

# Force UTF-8 output on Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if sys.stderr.encoding != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
PLUGIN_PROMPTS_DIR = os.path.join(PLUGIN_DIR, 'prompts')


def resolve_sources():
    """Return the ordered list of directories to search, highest-priority first."""
    sources = []
    env_dir = os.environ.get('N8N_PROMPTS_DIR')
    if env_dir:
        sources.append(('env', os.path.abspath(env_dir)))
    cwd = os.getcwd()
    sources.append(('project', os.path.join(cwd, '.n8n-files', 'prompts')))
    sources.append(('project', os.path.join(cwd, 'prompts')))
    sources.append(('plugin', PLUGIN_PROMPTS_DIR))
    return sources


def key_to_relpath(key):
    """Convert a prompt key (slash-separated, no extension) to a relative path."""
    key = key.strip().strip('/').replace('\\', '/')
    if not key:
        raise ValueError('empty prompt key')
    if '..' in key.split('/'):
        raise ValueError('prompt key must not contain ".."')
    return key + '.md'


def resolve(key):
    """Return (source_label, absolute_path) for the first matching source, or None."""
    rel = key_to_relpath(key)
    for label, directory in resolve_sources():
        if not os.path.isdir(directory):
            continue
        candidate = os.path.join(directory, rel)
        if os.path.isfile(candidate):
            return (label, os.path.abspath(candidate))
    return None


def cmd_get(key):
    hit = resolve(key)
    if not hit:
        print(f'prompt not found: {key}', file=sys.stderr)
        sys.exit(2)
    _, path = hit
    with open(path, 'r', encoding='utf-8') as f:
        sys.stdout.write(f.read())


def cmd_path(key):
    hit = resolve(key)
    if not hit:
        print(f'prompt not found: {key}', file=sys.stderr)
        sys.exit(2)
    _, path = hit
    print(path)


def cmd_list():
    """List unique keys across all source dirs. Earlier sources mask later ones."""
    seen = {}
    for label, directory in resolve_sources():
        if not os.path.isdir(directory):
            continue
        for root, _, files in os.walk(directory):
            for name in files:
                if not name.endswith('.md'):
                    continue
                full = os.path.join(root, name)
                rel = os.path.relpath(full, directory).replace('\\', '/')
                key = rel[:-3]  # drop .md
                if key not in seen:
                    seen[key] = (label, full)
    if not seen:
        print('(no prompts found)')
        return
    width = max(len(k) for k in seen)
    for key in sorted(seen):
        label, path = seen[key]
        print(f'{key:<{width}}  [{label}]  {path}')


def cmd_sources():
    for label, directory in resolve_sources():
        exists = 'yes' if os.path.isdir(directory) else 'no '
        print(f'{exists}  [{label:<7}]  {directory}')


def main():
    parser = argparse.ArgumentParser(
        description='Layered prompt loader for n8n workflows.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--get', metavar='KEY', help='print the resolved prompt body')
    group.add_argument('--path', metavar='KEY', help='print the resolved file path')
    group.add_argument('--list', action='store_true', help='list available prompt keys')
    group.add_argument('--sources', action='store_true', help='show the search path')
    args = parser.parse_args()

    if args.get:
        cmd_get(args.get)
    elif args.path:
        cmd_path(args.path)
    elif args.list:
        cmd_list()
    elif args.sources:
        cmd_sources()


if __name__ == '__main__':
    main()
