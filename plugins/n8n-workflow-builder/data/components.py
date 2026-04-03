#!/usr/bin/env python3
"""
n8n Reusable Component Library — Save, search, and reuse workflow patterns.

Usage:
    python3 components.py --save "Name" --category "cat" --description "desc" --code "SDK code" [--params '["p1","p2"]']
    python3 components.py --list [--category "cat"]
    python3 components.py --get "Name"
    python3 components.py --search "query"
    python3 components.py --delete "Name"
    python3 components.py --stats
"""

import json
import sys
import os
import io
import argparse
from datetime import datetime

# Force UTF-8 output on Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if sys.stderr.encoding != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

COMPONENTS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'components.json')


def load_library():
    if os.path.exists(COMPONENTS_FILE):
        with open(COMPONENTS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'components': []}


def save_library(lib):
    with open(COMPONENTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(lib, f, indent=2, ensure_ascii=False)


def save_component(name, category, description, code, params=None):
    lib = load_library()

    # Check for duplicate
    existing = [c for c in lib['components'] if c['name'] == name]
    if existing:
        # Update existing
        for c in lib['components']:
            if c['name'] == name:
                c['category'] = category
                c['description'] = description
                c['code'] = code
                c['params'] = params or []
                c['updated'] = datetime.now().isoformat()
        print(f'Updated component: "{name}"')
    else:
        lib['components'].append({
            'name': name,
            'category': category,
            'description': description,
            'code': code,
            'params': params or [],
            'created': datetime.now().isoformat(),
            'updated': datetime.now().isoformat(),
            'usageCount': 0
        })
        print(f'Saved new component: "{name}"')

    save_library(lib)
    print(f'Total components: {len(lib["components"])}')


def list_components(category=None):
    lib = load_library()
    components = lib['components']

    if category:
        components = [c for c in components if c.get('category', '').lower() == category.lower()]

    if not components:
        print('No components found.' + (f' Category: {category}' if category else ''))
        return

    for c in sorted(components, key=lambda x: x.get('category', '')):
        params = ', '.join(c.get('params', [])) if c.get('params') else 'none'
        uses = c.get('usageCount', 0)
        print(f'[{c.get("category", "?")}] {c["name"]} (params: {params}, used: {uses}x)')
        print(f'  {c.get("description", "")}')
        print()


def get_component(name):
    lib = load_library()
    for c in lib['components']:
        if c['name'].lower() == name.lower():
            # Increment usage count
            c['usageCount'] = c.get('usageCount', 0) + 1
            save_library(lib)
            print(json.dumps(c, indent=2, ensure_ascii=False))
            return
    print(f'Component not found: "{name}"')
    # Suggest similar
    matches = [c for c in lib['components'] if name.lower() in c['name'].lower() or name.lower() in c.get('description', '').lower()]
    if matches:
        print('Did you mean:')
        for m in matches:
            print(f'  - {m["name"]}')


def search_components(query):
    lib = load_library()
    query_lower = query.lower()
    matches = []
    for c in lib['components']:
        searchable = f'{c["name"]} {c.get("category", "")} {c.get("description", "")}'.lower()
        if query_lower in searchable:
            matches.append(c)

    if not matches:
        print(f'No components matching "{query}"')
        return

    for c in matches:
        params = ', '.join(c.get('params', [])) if c.get('params') else 'none'
        print(f'[{c.get("category", "?")}] {c["name"]}')
        print(f'  {c.get("description", "")}')
        print(f'  Params: {params}')
        print()
    print(f'{len(matches)} components found')


def delete_component(name):
    lib = load_library()
    before = len(lib['components'])
    lib['components'] = [c for c in lib['components'] if c['name'].lower() != name.lower()]
    after = len(lib['components'])

    if before == after:
        print(f'Component not found: "{name}"')
    else:
        save_library(lib)
        print(f'Deleted: "{name}". Remaining: {after}')


def show_stats():
    lib = load_library()
    components = lib['components']
    print(f'Total components: {len(components)}')

    categories = {}
    for c in components:
        cat = c.get('category', 'uncategorized')
        categories[cat] = categories.get(cat, 0) + 1

    if categories:
        print('By category:')
        for cat, count in sorted(categories.items()):
            print(f'  {cat}: {count}')

    total_uses = sum(c.get('usageCount', 0) for c in components)
    print(f'Total usage count: {total_uses}')

    if components:
        most_used = max(components, key=lambda c: c.get('usageCount', 0))
        if most_used.get('usageCount', 0) > 0:
            print(f'Most used: "{most_used["name"]}" ({most_used["usageCount"]}x)')


def main():
    parser = argparse.ArgumentParser(description='n8n Reusable Component Library')
    parser.add_argument('--save', metavar='NAME', help='Save a component')
    parser.add_argument('--category', metavar='CAT', help='Component category')
    parser.add_argument('--description', metavar='DESC', help='Component description')
    parser.add_argument('--code', metavar='CODE', help='SDK code snippet')
    parser.add_argument('--params', metavar='JSON', help='JSON array of parameter names')
    parser.add_argument('--list', action='store_true', help='List all components')
    parser.add_argument('--get', metavar='NAME', help='Get a component by name')
    parser.add_argument('--search', metavar='QUERY', help='Search components')
    parser.add_argument('--delete', metavar='NAME', help='Delete a component')
    parser.add_argument('--stats', action='store_true', help='Show library stats')
    args = parser.parse_args()

    if args.save:
        if not args.category or not args.description or not args.code:
            print('Error: --save requires --category, --description, and --code')
            return
        params = json.loads(args.params) if args.params else []
        save_component(args.save, args.category, args.description, args.code, params)
    elif args.list:
        list_components(args.category)
    elif args.get:
        get_component(args.get)
    elif args.search:
        search_components(args.search)
    elif args.delete:
        delete_component(args.delete)
    elif args.stats:
        show_stats()
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
