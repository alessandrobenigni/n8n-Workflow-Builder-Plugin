#!/usr/bin/env python3
"""
n8n Reusable Component Library — SQLite-backed, FTS5-searchable.

Components are saved in the same nodes.db database as official nodes.
Searches return BOTH official nodes and custom components together.

Usage:
    python3 components.py --save "Name" --category "cat" --description "desc" --code "SDK code" [--params '["p1"]'] [--tags "error-handling, notification"]
    python3 components.py --list [--category "cat"]
    python3 components.py --get "Name"
    python3 components.py --search "query"
    python3 components.py --delete "Name"
    python3 components.py --stats
"""

import sqlite3
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

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'nodes.db')


def get_conn():
    return sqlite3.connect(DB_PATH)


def save_component(name, category, description, code, params=None, tags=None, node_types_used=None):
    """Save or update a component in the database."""
    conn = get_conn()
    cur = conn.cursor()

    tags_str = ', '.join(tags) if tags else category
    params_str = json.dumps(params or [])
    node_types_str = ', '.join(node_types_used) if node_types_used else ''
    now = datetime.now().isoformat()

    # Upsert: update if exists, insert if new
    cur.execute('SELECT id FROM custom_components WHERE name = ?', (name,))
    existing = cur.fetchone()

    if existing:
        cur.execute('''
            UPDATE custom_components
            SET description = ?, category = ?, tags = ?, sdk_code = ?,
                node_types_used = ?, params = ?, updated_at = ?
            WHERE name = ?
        ''', (description, category, tags_str, code, node_types_str, params_str, now, name))
        print(f'Updated component: "{name}"')
    else:
        cur.execute('''
            INSERT INTO custom_components (name, description, category, tags, sdk_code, node_types_used, params, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (name, description, category, tags_str, code, node_types_str, params_str, now, now))
        print(f'Saved new component: "{name}"')

    conn.commit()

    cur.execute('SELECT COUNT(*) FROM custom_components')
    print(f'Total components: {cur.fetchone()[0]}')
    conn.close()


def list_components(category=None):
    """List all components, optionally filtered by category."""
    conn = get_conn()
    cur = conn.cursor()

    if category:
        cur.execute('''
            SELECT name, category, description, tags, params, usage_count, created_at
            FROM custom_components WHERE LOWER(category) = LOWER(?) ORDER BY category, name
        ''', (category,))
    else:
        cur.execute('''
            SELECT name, category, description, tags, params, usage_count, created_at
            FROM custom_components ORDER BY category, name
        ''')

    rows = cur.fetchall()
    conn.close()

    if not rows:
        print('No components found.' + (f' Category: {category}' if category else ''))
        return

    for name, cat, desc, tags, params_json, uses, created in rows:
        params = json.loads(params_json) if params_json else []
        params_str = ', '.join(params) if params else 'none'
        print(f'[{cat}] {name} (params: {params_str}, used: {uses}x)')
        print(f'  {desc}')
        if tags:
            print(f'  tags: {tags}')
        print()


def get_component(name):
    """Get a component by name, increment usage count."""
    conn = get_conn()
    cur = conn.cursor()

    cur.execute('''
        SELECT name, category, description, tags, sdk_code, node_types_used, params, usage_count, created_at, updated_at
        FROM custom_components WHERE LOWER(name) = LOWER(?)
    ''', (name,))
    row = cur.fetchone()

    if not row:
        conn.close()
        print(f'Component not found: "{name}"')
        # Suggest similar via FTS
        cur2 = get_conn().cursor()
        try:
            cur2.execute("SELECT name FROM custom_components_fts WHERE custom_components_fts MATCH ? LIMIT 5", (name,))
            matches = cur2.fetchall()
            if matches:
                print('Did you mean:')
                for (m,) in matches:
                    print(f'  - {m}')
        except Exception:
            pass
        return

    # Increment usage count
    cur.execute('UPDATE custom_components SET usage_count = usage_count + 1 WHERE LOWER(name) = LOWER(?)', (name,))
    conn.commit()
    conn.close()

    result = {
        'name': row[0],
        'category': row[1],
        'description': row[2],
        'tags': row[3],
        'code': row[4],
        'node_types_used': row[5],
        'params': json.loads(row[6]) if row[6] else [],
        'usage_count': row[7] + 1,
        'created_at': row[8],
        'updated_at': row[9]
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))


def search_components(query):
    """Search components using FTS5 + LIKE fallback."""
    conn = get_conn()
    cur = conn.cursor()
    results = []

    # Strategy 1: FTS5 search
    try:
        words = query.strip().split()
        or_query = ' OR '.join(w for w in words if len(w) >= 2)
        if or_query:
            cur.execute('''
                SELECT c.name, c.category, c.description, c.tags, c.params, c.usage_count, rank
                FROM custom_components_fts f
                JOIN custom_components c ON c.rowid = f.rowid
                WHERE custom_components_fts MATCH ?
                ORDER BY rank
                LIMIT 20
            ''', (or_query,))
            results = cur.fetchall()
    except Exception:
        pass

    # Strategy 2: LIKE fallback
    if not results:
        cur.execute('''
            SELECT name, category, description, tags, params, usage_count, 0
            FROM custom_components
            WHERE LOWER(name) LIKE ? OR LOWER(description) LIKE ? OR LOWER(tags) LIKE ? OR LOWER(category) LIKE ?
            LIMIT 20
        ''', (f'%{query.lower()}%',) * 4)
        results = cur.fetchall()

    conn.close()

    if not results:
        print(f'No components matching "{query}"')
        return

    for name, cat, desc, tags, params_json, uses, rank in results:
        params = json.loads(params_json) if params_json else []
        params_str = ', '.join(params) if params else 'none'
        print(f'[COMPONENT] [{cat}] {name} (params: {params_str}, used: {uses}x)')
        print(f'  {desc}')
        print()
    print(f'{len(results)} components found for "{query}"')


def delete_component(name):
    """Delete a component by name."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('SELECT id FROM custom_components WHERE LOWER(name) = LOWER(?)', (name,))
    if not cur.fetchone():
        print(f'Component not found: "{name}"')
        conn.close()
        return

    cur.execute('DELETE FROM custom_components WHERE LOWER(name) = LOWER(?)', (name,))
    conn.commit()
    conn.close()
    print(f'Deleted: "{name}"')


def show_stats():
    """Show component library statistics."""
    conn = get_conn()
    cur = conn.cursor()

    cur.execute('SELECT COUNT(*) FROM custom_components')
    total = cur.fetchone()[0]

    cur.execute('SELECT category, COUNT(*) FROM custom_components GROUP BY category ORDER BY COUNT(*) DESC')
    categories = cur.fetchall()

    cur.execute('SELECT SUM(usage_count) FROM custom_components')
    total_uses = cur.fetchone()[0] or 0

    # Also show official node count for context
    cur.execute('SELECT COUNT(*) FROM nodes')
    official_nodes = cur.fetchone()[0]

    conn.close()

    print(f'Custom components: {total}')
    print(f'Official n8n nodes: {official_nodes}')
    print(f'Total in database: {total + official_nodes}')
    print()

    if categories:
        print('Components by category:')
        for cat, count in categories:
            print(f'  {cat}: {count}')

    print(f'Total component usage: {total_uses}')

    if total > 0:
        conn2 = get_conn()
        cur2 = conn2.cursor()
        cur2.execute('SELECT name, usage_count FROM custom_components ORDER BY usage_count DESC LIMIT 1')
        most = cur2.fetchone()
        conn2.close()
        if most and most[1] > 0:
            print(f'Most used: "{most[0]}" ({most[1]}x)')


def main():
    parser = argparse.ArgumentParser(description='n8n Reusable Component Library (SQLite-backed)')
    parser.add_argument('--save', metavar='NAME', help='Save a component')
    parser.add_argument('--category', metavar='CAT', help='Component category')
    parser.add_argument('--description', metavar='DESC', help='Component description')
    parser.add_argument('--code', metavar='CODE', help='SDK code snippet')
    parser.add_argument('--params', metavar='JSON', help='JSON array of parameter names')
    parser.add_argument('--tags', metavar='TAGS', help='Comma-separated tags')
    parser.add_argument('--nodes', metavar='NODES', help='Comma-separated node types used')
    parser.add_argument('--list', action='store_true', help='List all components')
    parser.add_argument('--get', metavar='NAME', help='Get a component by name')
    parser.add_argument('--search', metavar='QUERY', help='Search components (uses FTS5)')
    parser.add_argument('--delete', metavar='NAME', help='Delete a component')
    parser.add_argument('--stats', action='store_true', help='Show library stats')
    args = parser.parse_args()

    if args.save:
        if not args.category or not args.description or not args.code:
            print('Error: --save requires --category, --description, and --code')
            return
        params = json.loads(args.params) if args.params else []
        tags = [t.strip() for t in args.tags.split(',')] if args.tags else None
        nodes = [n.strip() for n in args.nodes.split(',')] if args.nodes else None
        save_component(args.save, args.category, args.description, args.code, params, tags, nodes)
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
