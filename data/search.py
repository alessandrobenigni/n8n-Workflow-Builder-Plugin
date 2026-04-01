#!/usr/bin/env python3
"""
n8n Node Search Utility — Production-grade semantic search across 1,396 nodes.

Combines 6 search strategies with synonym expansion, OR-based FTS5 queries,
operations-aware matching, and intelligent scoring to find nodes by what they DO,
not just what they're called.

Usage:
    python3 search.py "query" [--limit N] [--triggers-only] [--ai-only] [--core-only] [--no-tool-variants]
    python3 search.py --node NODE_TYPE                               # Full node details
    python3 search.py --schema NODE_TYPE [--resource R --operation O] # Properties schema
    python3 search.py --template-configs NODE_TYPE                   # Real-world config examples
    python3 search.py --template-search "query"                      # Search workflow templates
    python3 search.py --list-triggers                                # List all trigger nodes
    python3 search.py --list-ai                                      # List all AI/LangChain nodes
    python3 search.py --stats                                        # Database statistics
"""

import sqlite3
import json
import sys
import os
import argparse
import re
from collections import defaultdict

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'nodes.db')

# ─── Synonym Expansion ──────────────────────────────────────────────────────
# Maps user intent words to multiple search terms that cover all relevant nodes.
# This is THE critical piece — "send notification" must find Slack, Gmail, Telegram, etc.
SYNONYMS = {
    # Messaging / Notification intent
    'notification': ['slack', 'telegram', 'discord', 'email', 'sms', 'twilio', 'whatsapp', 'gmail', 'sendgrid', 'pushover', 'gotify', 'teams', 'message', 'notify', 'alert', 'send'],
    'notify': ['slack', 'telegram', 'discord', 'email', 'sms', 'twilio', 'whatsapp', 'gmail', 'sendgrid', 'teams', 'message', 'send'],
    'alert': ['slack', 'telegram', 'discord', 'email', 'sms', 'twilio', 'notification', 'pagerduty', 'opsgenie'],
    'message': ['slack', 'telegram', 'discord', 'whatsapp', 'teams', 'sms', 'twilio', 'email', 'chat', 'send'],
    'chat': ['slack', 'telegram', 'discord', 'whatsapp', 'teams', 'chatTrigger', 'agent', 'chatbot', 'conversational'],
    'email': ['gmail', 'outlook', 'emailSend', 'sendgrid', 'mailchimp', 'ses', 'smtp', 'imap', 'mailjet', 'mandrill', 'brevo'],

    # Database / Storage intent
    'database': ['postgres', 'mysql', 'mongodb', 'redis', 'elasticsearch', 'supabase', 'dataTable', 'dynamodb', 'msSql', 'snowflake', 'bigquery', 'sqlite', 'firestore'],
    'storage': ['s3', 'googleDrive', 'dropbox', 'oneDrive', 'googleCloudStorage', 'azureStorage', 'ftp', 'sftp'],
    'store': ['postgres', 'mysql', 'mongodb', 'redis', 'dataTable', 'googleSheets', 'airtable', 'notion', 'supabase', 'baserow'],
    'persist': ['dataTable', 'postgres', 'mysql', 'mongodb', 'googleSheets', 'airtable'],
    'spreadsheet': ['googleSheets', 'microsoftExcel', 'airtable', 'baserow', 'seaTable', 'spreadsheetFile'],

    # AI / LLM intent
    'ai': ['agent', 'openAi', 'anthropic', 'gemini', 'ollama', 'langchain', 'lmChat', 'llm', 'chatbot'],
    'llm': ['lmChatOpenAi', 'lmChatAnthropic', 'lmChatGoogleGemini', 'lmChatOllama', 'lmChatGroq', 'lmChatMistral', 'lmChatDeepSeek', 'agent'],
    'chatbot': ['chatTrigger', 'agent', 'memoryBufferWindow', 'lmChatOpenAi', 'conversational'],
    'rag': ['vectorStore', 'embeddings', 'retriever', 'documentLoader', 'textSplitter', 'agent'],
    'embeddings': ['embeddingsOpenAi', 'embeddingsGoogleGemini', 'embeddingsOllama', 'embeddingsCohere', 'embeddingsMistral', 'embeddingsAzure'],
    'vector': ['vectorStore', 'pinecone', 'qdrant', 'chroma', 'weaviate', 'supabase', 'pgvector', 'milvus', 'redis', 'inMemory'],

    # Trigger intent
    'schedule': ['scheduleTrigger', 'cron', 'interval'],
    'webhook': ['webhook', 'respondToWebhook', 'httpRequest'],
    'trigger': ['trigger', 'scheduleTrigger', 'webhook', 'formTrigger', 'chatTrigger', 'emailReadImap'],
    'cron': ['scheduleTrigger', 'interval', 'schedule'],

    # Data transformation intent
    'transform': ['set', 'code', 'filter', 'sort', 'aggregate', 'summarize', 'splitOut', 'merge', 'removeDuplicates', 'renameKeys', 'itemLists'],
    'filter': ['filter', 'if', 'switch', 'removeDuplicates'],
    'merge': ['merge', 'aggregate', 'summarize', 'compareDatasets'],
    'loop': ['splitInBatches', 'loop', 'forEach'],
    'branch': ['if', 'switch', 'filter'],
    'condition': ['if', 'switch', 'filter'],

    # Web / Scraping intent
    'scrape': ['httpRequest', 'htmlExtract', 'html', 'airtop', 'phantombuster', 'code'],
    'crawl': ['httpRequest', 'htmlExtract', 'html', 'airtop', 'code'],
    'extract': ['extractFromFile', 'htmlExtract', 'html', 'informationExtractor', 'code'],
    'pdf': ['readPDF', 'extractFromFile', 'convertToFile', 'awsTextract', 'mindee'],

    # CRM intent
    'crm': ['hubspot', 'salesforce', 'pipedrive', 'zohoCrm', 'freshworksCrm', 'copper', 'activeCampaign'],
    'leads': ['hubspot', 'salesforce', 'pipedrive', 'activeCampaign', 'crm'],

    # Project management intent
    'project': ['jira', 'linear', 'trello', 'asana', 'clickUp', 'todoist', 'github', 'gitlab'],
    'task': ['jira', 'linear', 'trello', 'asana', 'clickUp', 'todoist', 'googleTasks', 'microsoftToDo'],
    'issue': ['jira', 'linear', 'github', 'gitlab', 'sentry'],

    # Payment intent
    'payment': ['stripe', 'shopify', 'paypal', 'square'],
    'invoice': ['stripe', 'shopify', 'quickbooks', 'xero', 'freshbooks'],
    'ecommerce': ['shopify', 'woocommerce', 'stripe', 'magento'],

    # File / Document intent
    'file': ['googleDrive', 'dropbox', 'oneDrive', 's3', 'ftp', 'sftp', 'extractFromFile', 'convertToFile', 'readWriteFile', 'compression'],
    'document': ['googleDocs', 'notion', 'documentLoader', 'extractFromFile', 'readPDF', 'awsTextract'],
    'image': ['editImage', 'openAi', 'googleGemini', 'cloudinary'],
    'video': ['youtube', 'openAi', 'googleGemini', 'vimeo'],
    'audio': ['openAi', 'googleGemini', 'twilio', 'assemblyai'],
}

# ─── Scoring Weights ────────────────────────────────────────────────────────
SCORE_FTS_EXACT = 10.0      # FTS5 match (highest - actual text match)
SCORE_NAME_EXACT = 9.0      # display_name contains the exact query
SCORE_SYNONYM_HIT = 7.0     # Synonym expansion match on node_type
SCORE_OPERATIONS = 6.0      # Match found in operations JSON
SCORE_DESCRIPTION = 5.0     # LIKE match on description
SCORE_AI_SUMMARY = 4.0      # Match in AI-generated summary
SCORE_DOCUMENTATION = 3.0   # Match in full documentation text


def get_conn():
    return sqlite3.connect(DB_PATH)


def to_sdk_format(db_type):
    """Convert DB node_type to SDK format for code generation."""
    if db_type.startswith('nodes-base.'):
        return 'n8n-' + db_type
    elif db_type.startswith('nodes-langchain.'):
        return '@n8n/n8n-' + db_type
    return db_type


def from_sdk_format(sdk_type):
    """Convert SDK node_type back to DB format for lookups."""
    if sdk_type.startswith('n8n-nodes-base.'):
        return sdk_type[4:]  # strip 'n8n-'
    elif sdk_type.startswith('@n8n/n8n-nodes-langchain.'):
        return sdk_type[5:]  # strip '@n8n/'  -> becomes 'n8n-nodes-langchain.X' ... wrong
    # Actually: @n8n/n8n-nodes-langchain.X -> nodes-langchain.X
    if sdk_type.startswith('@n8n/n8n-'):
        return sdk_type[9:]  # strip '@n8n/n8n-'
    return sdk_type


def _expand_query(query):
    """Expand a query with synonyms. Returns list of additional search terms."""
    words = query.lower().split()
    expanded = set()
    for word in words:
        if word in SYNONYMS:
            expanded.update(SYNONYMS[word])
        # Also check 2-word combos
    phrase = query.lower()
    for key in SYNONYMS:
        if key in phrase:
            expanded.update(SYNONYMS[key])
    return list(expanded)


def _fts_or_query(words):
    """Build an FTS5 OR query from a list of words."""
    # Escape special FTS characters
    safe = []
    for w in words:
        w = w.strip()
        if w and len(w) >= 2:
            # Remove FTS5 special chars
            w = re.sub(r'[^\w]', '', w)
            if w:
                safe.append(w)
    if not safe:
        return None
    return ' OR '.join(safe)


NODE_COLS = (
    "node_type, display_name, description, category, is_trigger, is_ai_tool, "
    "is_tool_variant, is_community, is_verified, version"
)


def search_nodes(query, limit=15, category=None, triggers_only=False, ai_only=False,
                 core_only=False, no_tool_variants=False, exclude_community=False):
    """
    Multi-strategy semantic node search.

    Strategies (in order of score):
    1. FTS5 with original query (exact relevance)
    2. Exact display_name match (boosted)
    3. FTS5 with OR-expanded synonyms (broader recall)
    4. Synonym match on node_type (catches nodes whose names match synonym terms)
    5. Operations JSON search (finds nodes by what they CAN DO)
    6. AI documentation summary search (semantic intent)
    7. Full documentation text search (deepest recall)

    Results are deduplicated and scored. Higher score = more relevant.
    """
    conn = get_conn()
    cur = conn.cursor()
    scored = {}  # node_type -> (best_score, row_data)

    def _add(node_type, score, row):
        if node_type in scored:
            # Keep highest score, but boost nodes that appear in multiple strategies
            old_score = scored[node_type][0]
            scored[node_type] = (max(old_score, score) + 0.5, row)  # +0.5 multi-hit bonus
        else:
            scored[node_type] = (score, row)

    query_lower = query.lower().strip()
    query_words = query_lower.split()

    # ── Strategy 1: FTS5 full-text search with original query ──
    try:
        # Try exact phrase first (quoted)
        fts_query = f'"{query_lower}"'
        cur.execute(
            f"SELECT {NODE_COLS}, rank FROM nodes_fts WHERE nodes_fts MATCH ? ORDER BY rank LIMIT ?",
            (fts_query, limit * 2)
        )
        for r in cur.fetchall():
            # FTS5 BM25 rank is negative; convert to positive score
            fts_score = SCORE_FTS_EXACT + (-r[10] / 5.0)
            _add(r[0], fts_score, r[:10])
    except Exception:
        pass

    # Also try individual words with OR
    try:
        or_query = _fts_or_query(query_words)
        if or_query:
            cur.execute(
                f"SELECT {NODE_COLS}, rank FROM nodes_fts WHERE nodes_fts MATCH ? ORDER BY rank LIMIT ?",
                (or_query, limit * 3)
            )
            for r in cur.fetchall():
                fts_score = SCORE_FTS_EXACT - 1.0 + (-r[10] / 5.0)
                _add(r[0], fts_score, r[:10])
    except Exception:
        pass

    # ── Strategy 2: Exact display_name match (boosted) ──
    cur.execute(
        f"SELECT {NODE_COLS} FROM nodes WHERE LOWER(display_name) = ?",
        (query_lower,)
    )
    for r in cur.fetchall():
        _add(r[0], SCORE_NAME_EXACT + 5.0, r)  # Big boost for exact name

    # Partial display_name match
    for word in query_words:
        if len(word) >= 2:
            cur.execute(
                f"SELECT {NODE_COLS} FROM nodes WHERE LOWER(display_name) LIKE ?",
                (f'%{word}%',)
            )
            for r in cur.fetchall():
                _add(r[0], SCORE_NAME_EXACT, r)

    # ── Strategy 3: FTS5 with synonym-expanded OR query ──
    synonyms = _expand_query(query)
    if synonyms:
        # Search for synonym terms in FTS
        syn_or = _fts_or_query(synonyms[:20])  # Cap at 20 to avoid huge queries
        if syn_or:
            try:
                cur.execute(
                    f"SELECT {NODE_COLS}, rank FROM nodes_fts WHERE nodes_fts MATCH ? ORDER BY rank LIMIT ?",
                    (syn_or, limit * 3)
                )
                for r in cur.fetchall():
                    _add(r[0], SCORE_SYNONYM_HIT + (-r[10] / 10.0), r[:10])
            except Exception:
                pass

    # ── Strategy 4: Synonym match on node_type directly ──
    if synonyms:
        for syn in synonyms:
            syn_lower = syn.lower()
            cur.execute(
                f"SELECT {NODE_COLS} FROM nodes WHERE LOWER(node_type) LIKE ? LIMIT ?",
                (f'%{syn_lower}%', limit)
            )
            for r in cur.fetchall():
                _add(r[0], SCORE_SYNONYM_HIT, r)

    # ── Strategy 5: Operations JSON search ──
    # This finds nodes that can PERFORM the action the user describes
    for word in query_words:
        if len(word) >= 3:
            cur.execute(
                f"SELECT {NODE_COLS} FROM nodes WHERE LOWER(operations) LIKE ? LIMIT ?",
                (f'%"{word}%', limit * 2)
            )
            for r in cur.fetchall():
                _add(r[0], SCORE_OPERATIONS, r)

    # ── Strategy 6: AI documentation summary search ──
    for word in query_words:
        if len(word) >= 3:
            cur.execute(
                f"SELECT {NODE_COLS} FROM nodes WHERE LOWER(ai_documentation_summary) LIKE ? LIMIT ?",
                (f'%{word}%', limit)
            )
            for r in cur.fetchall():
                _add(r[0], SCORE_AI_SUMMARY, r)

    # ── Strategy 7: Full documentation text search ──
    for word in query_words:
        if len(word) >= 4:  # Longer words only to avoid noise
            cur.execute(
                f"SELECT {NODE_COLS} FROM nodes WHERE LOWER(documentation) LIKE ? LIMIT ?",
                (f'%{word}%', limit)
            )
            for r in cur.fetchall():
                _add(r[0], SCORE_DOCUMENTATION, r)

    conn.close()

    # ── Apply filters ──
    filtered = []
    for node_type, (score, row) in scored.items():
        if triggers_only and not row[4]:
            continue
        if ai_only and not row[5]:
            continue
        if core_only and row[7]:  # is_community
            continue
        if exclude_community and row[7]:
            continue
        if no_tool_variants and row[6]:  # is_tool_variant
            continue
        if category:
            node_cat = (row[3] or '').lower()
            if category.lower() not in node_cat:
                continue
        filtered.append((score, node_type, row))

    # Sort by score descending (highest = most relevant)
    filtered.sort(key=lambda x: -x[0])

    return filtered[:limit]


def get_node_details(node_type):
    """Get full details for a specific node, including all metadata."""
    conn = get_conn()
    cur = conn.cursor()

    # Try exact match first
    cur.execute(
        "SELECT node_type, display_name, description, category, is_trigger, is_ai_tool, "
        "is_tool_variant, has_tool_variant, base_node_type, tool_variant_of, "
        "is_community, is_verified, version, package_name, "
        "credentials_required, operations, outputs, output_names, "
        "ai_documentation_summary, development_style, is_versioned, is_webhook "
        "FROM nodes WHERE node_type = ?",
        (node_type,)
    )
    row = cur.fetchone()

    # Try with SDK format conversion
    if not row:
        db_type = from_sdk_format(node_type)
        cur.execute(
            "SELECT node_type, display_name, description, category, is_trigger, is_ai_tool, "
            "is_tool_variant, has_tool_variant, base_node_type, tool_variant_of, "
            "is_community, is_verified, version, package_name, "
            "credentials_required, operations, outputs, output_names, "
            "ai_documentation_summary, development_style, is_versioned, is_webhook "
            "FROM nodes WHERE node_type = ?",
            (db_type,)
        )
        row = cur.fetchone()

    conn.close()
    if not row:
        return None

    return {
        'node_type': row[0],
        'sdk_type': to_sdk_format(row[0]),
        'display_name': row[1],
        'description': row[2],
        'category': row[3],
        'is_trigger': bool(row[4]),
        'is_ai_tool': bool(row[5]),
        'is_tool_variant': bool(row[6]),
        'has_tool_variant': bool(row[7]),
        'base_node_type': row[8],
        'tool_variant_of': row[9],
        'is_community': bool(row[10]),
        'is_verified': bool(row[11]),
        'version': row[12],
        'package_name': row[13],
        'credentials': json.loads(row[14]) if row[14] else [],
        'operations': json.loads(row[15]) if row[15] else [],
        'outputs': row[16],
        'output_names': row[17],
        'ai_summary': json.loads(row[18]) if row[18] else None,
        'development_style': row[19],
        'is_versioned': bool(row[20]),
        'is_webhook': bool(row[21]),
    }


def get_node_schema(node_type, resource=None, operation=None):
    """
    Get properties schema for a node, optionally filtered by resource/operation.
    Understands displayOptions.show to return only relevant fields.
    """
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT properties_schema, version FROM nodes WHERE node_type = ?", (node_type,))
    row = cur.fetchone()
    if not row:
        # Try SDK format conversion
        db_type = from_sdk_format(node_type)
        cur.execute("SELECT properties_schema, version FROM nodes WHERE node_type = ?", (db_type,))
        row = cur.fetchone()
    conn.close()

    if not row or not row[0]:
        return None

    schema = json.loads(row[0])

    if resource or operation:
        filtered = []
        for prop in schema:
            display_options = prop.get('displayOptions', {})
            show = display_options.get('show', {})
            hide = display_options.get('hide', {})

            # If no display restrictions, always include
            if not show and not hide:
                filtered.append(prop)
                continue

            # Check show conditions
            include = True
            if show:
                if resource and 'resource' in show:
                    if resource not in show['resource']:
                        include = False
                if operation and 'operation' in show:
                    if operation not in show['operation']:
                        include = False

            # Check hide conditions
            if hide:
                if resource and 'resource' in hide:
                    if resource in hide['resource']:
                        include = False
                if operation and 'operation' in hide:
                    if operation in hide['operation']:
                        include = False

            if include:
                filtered.append(prop)
        return {'version': row[1], 'properties': filtered, 'total_properties': len(schema)}

    return {'version': row[1], 'properties': schema, 'total_properties': len(schema)}


def get_template_configs(node_type):
    """Get real-world config examples from popular templates, ranked by popularity."""
    conn = get_conn()
    cur = conn.cursor()

    # Try exact match
    cur.execute(
        "SELECT parameters_json, template_name, template_views, node_name, "
        "has_credentials, has_expressions, complexity, use_cases "
        "FROM template_node_configs WHERE node_type = ? ORDER BY template_views DESC LIMIT 5",
        (node_type,)
    )
    rows = cur.fetchall()

    # Try partial match on node type suffix
    if not rows:
        suffix = node_type.split('.')[-1] if '.' in node_type else node_type
        cur.execute(
            "SELECT parameters_json, template_name, template_views, node_name, "
            "has_credentials, has_expressions, complexity, use_cases "
            "FROM template_node_configs WHERE node_type LIKE ? ORDER BY template_views DESC LIMIT 5",
            (f'%{suffix}%',)
        )
        rows = cur.fetchall()

    conn.close()
    return [{
        'parameters': json.loads(r[0]) if r[0] else {},
        'template_name': r[1],
        'views': r[2],
        'node_name': r[3],
        'has_credentials': bool(r[4]),
        'has_expressions': bool(r[5]),
        'complexity': r[6],
        'use_cases': r[7],
    } for r in rows]


def search_templates(query, limit=10):
    """Search workflow templates by name/description."""
    conn = get_conn()
    cur = conn.cursor()
    results = []

    # Strategy 1: FTS5 search
    try:
        or_query = _fts_or_query(query.split())
        if or_query:
            cur.execute(
                "SELECT t.id, t.name, t.description, t.views, t.nodes_used, t.categories "
                "FROM templates t "
                "JOIN templates_fts f ON t.rowid = f.rowid "
                "WHERE templates_fts MATCH ? "
                "ORDER BY rank LIMIT ?",
                (or_query, limit)
            )
            results = cur.fetchall()
    except Exception:
        pass

    # Strategy 2: LIKE fallback
    if not results:
        for word in query.split():
            if len(word) >= 3:
                cur.execute(
                    "SELECT id, name, description, views, nodes_used, categories "
                    "FROM templates WHERE LOWER(name) LIKE ? OR LOWER(description) LIKE ? "
                    "ORDER BY views DESC LIMIT ?",
                    (f'%{word.lower()}%', f'%{word.lower()}%', limit)
                )
                results.extend(cur.fetchall())

    conn.close()

    # Deduplicate by id
    seen = set()
    unique = []
    for r in results:
        if r[0] not in seen:
            seen.add(r[0])
            unique.append(r)

    return [{
        'id': r[0],
        'name': r[1],
        'description': (r[2] or '')[:200],
        'views': r[3],
        'nodes_used': r[4],
        'categories': r[5],
    } for r in unique[:limit]]


def list_triggers():
    """List all trigger nodes."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        f"SELECT {NODE_COLS} FROM nodes WHERE is_trigger = 1 ORDER BY node_type"
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def list_ai_nodes():
    """List all AI/LangChain nodes (non-tool-variant)."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        f"SELECT {NODE_COLS} FROM nodes WHERE "
        "(node_type LIKE 'nodes-langchain.%' OR node_type LIKE '%langchain%') "
        "AND is_tool_variant = 0 ORDER BY node_type"
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def db_stats():
    """Get database statistics."""
    conn = get_conn()
    cur = conn.cursor()
    stats = {}
    cur.execute("SELECT COUNT(*) FROM nodes")
    stats['total_nodes'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM nodes WHERE is_community = 0 OR is_community IS NULL")
    stats['core_nodes'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM nodes WHERE is_community = 1")
    stats['community_nodes'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM nodes WHERE is_trigger = 1")
    stats['triggers'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM nodes WHERE is_ai_tool = 1")
    stats['ai_capable'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM nodes WHERE is_tool_variant = 1")
    stats['tool_variants'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM nodes WHERE is_verified = 1")
    stats['verified'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM nodes WHERE properties_schema IS NOT NULL AND LENGTH(properties_schema) > 10")
    stats['with_schema'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM templates")
    stats['templates'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM template_node_configs")
    stats['template_configs'] = cur.fetchone()[0]
    conn.close()
    return stats


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='n8n Node Search — Semantic search across 1,396 nodes')
    parser.add_argument('query', nargs='?', help='Search query (natural language)')
    parser.add_argument('--limit', '-n', type=int, default=15, help='Max results (default: 15)')
    parser.add_argument('--triggers-only', '-t', action='store_true', help='Only show trigger nodes')
    parser.add_argument('--ai-only', '-a', action='store_true', help='Only show AI-capable nodes')
    parser.add_argument('--core-only', '-c', action='store_true', help='Exclude community nodes')
    parser.add_argument('--no-tool-variants', action='store_true', help='Exclude tool variant nodes')
    parser.add_argument('--node', help='Get full details for a node (DB or SDK format)')
    parser.add_argument('--schema', help='Get properties schema for a node')
    parser.add_argument('--resource', help='Filter schema by resource')
    parser.add_argument('--operation', help='Filter schema by operation')
    parser.add_argument('--template-configs', help='Get real-world configs for a node')
    parser.add_argument('--template-search', help='Search workflow templates')
    parser.add_argument('--list-triggers', action='store_true', help='List all trigger nodes')
    parser.add_argument('--list-ai', action='store_true', help='List all AI/LangChain nodes')
    parser.add_argument('--stats', action='store_true', help='Show database statistics')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    args = parser.parse_args()

    if args.stats:
        stats = db_stats()
        if args.json:
            print(json.dumps(stats, indent=2))
        else:
            for k, v in stats.items():
                print(f'  {k}: {v}')
        return

    if args.list_triggers:
        rows = list_triggers()
        for r in rows:
            sdk = to_sdk_format(r[0])
            community = ' [COMMUNITY]' if r[7] else ''
            print(f'{sdk} | {r[1]} v{r[9]}{community}')
        print(f'\n{len(rows)} trigger nodes')
        return

    if args.list_ai:
        rows = list_ai_nodes()
        for r in rows:
            sdk = to_sdk_format(r[0])
            print(f'{sdk} | {r[1]} v{r[9]}')
        print(f'\n{len(rows)} AI/LangChain nodes')
        return

    if args.node:
        details = get_node_details(args.node)
        if details:
            if args.json:
                print(json.dumps(details, indent=2, default=str))
            else:
                print(f'  Node: {details["display_name"]} ({details["sdk_type"]})')
                print(f'  Version: {details["version"]}')
                print(f'  Category: {details["category"]}')
                flags = []
                if details['is_trigger']: flags.append('TRIGGER')
                if details['is_ai_tool']: flags.append('AI-CAPABLE')
                if details['is_tool_variant']: flags.append('TOOL-VARIANT')
                if details['is_community']: flags.append('COMMUNITY')
                if details['is_verified']: flags.append('VERIFIED')
                if details['is_webhook']: flags.append('WEBHOOK')
                print(f'  Flags: {", ".join(flags) if flags else "none"}')
                if details['has_tool_variant']:
                    print(f'  Has tool variant: yes')
                if details['tool_variant_of']:
                    print(f'  Tool variant of: {details["tool_variant_of"]}')
                print(f'  Description: {details["description"]}')
                if details['operations']:
                    print(f'  Operations ({len(details["operations"])}):')
                    for op in details['operations'][:20]:
                        res = op.get('resource', '')
                        name = op.get('operation', op.get('name', ''))
                        desc = op.get('description', '')[:60]
                        print(f'    {res}/{name}' + (f' — {desc}' if desc else ''))
                if details['credentials']:
                    print(f'  Credentials:')
                    for cred in details['credentials']:
                        print(f'    {cred.get("name", "?")} (required={cred.get("required", False)})')
                if details['ai_summary']:
                    summary = details['ai_summary']
                    if isinstance(summary, dict):
                        purpose = summary.get('purpose', '')
                        if purpose:
                            print(f'  AI Summary: {purpose[:200]}')
        else:
            print(f'Node not found: {args.node}')
            # Suggest similar
            results = search_nodes(args.node.split('.')[-1], limit=5)
            if results:
                print('  Did you mean:')
                for _, nt, row in results:
                    print(f'    {to_sdk_format(nt)} ({row[1]})')
        return

    if args.schema:
        schema = get_node_schema(args.schema, resource=args.resource, operation=args.operation)
        if schema:
            if args.json:
                print(json.dumps(schema, indent=2, default=str))
            else:
                filtered = 'filtered' if args.resource or args.operation else 'total'
                print(f'Version: {schema["version"]}')
                print(f'Properties: {len(schema["properties"])} {filtered} (of {schema["total_properties"]} total)')
                if args.resource:
                    print(f'Filtered by: resource={args.resource}' + (f', operation={args.operation}' if args.operation else ''))
                for p in schema['properties']:
                    name = p.get('name', '?')
                    ptype = p.get('type', '?')
                    required = p.get('required', False)
                    default = p.get('default', '')
                    desc = (p.get('description', '') or '')[:80]
                    options_str = ''
                    if p.get('options'):
                        opts = [str(o.get('value', o.get('name', ''))) for o in p['options'][:8]]
                        options_str = f' [{", ".join(opts)}]'
                    req = ' REQUIRED' if required else ''
                    print(f'  {name} ({ptype}){req} default={repr(default)}{options_str}')
                    if desc:
                        print(f'    {desc}')
        else:
            print(f'Schema not found for: {args.schema}')
        return

    if args.template_configs:
        configs = get_template_configs(args.template_configs)
        if configs:
            for c in configs:
                print(f'Template: {c["template_name"]} ({c["views"]} views)')
                print(f'  Node name: {c["node_name"]}')
                print(f'  Complexity: {c["complexity"]}')
                if c['use_cases']:
                    print(f'  Use cases: {c["use_cases"]}')
                params_str = json.dumps(c['parameters'], indent=2)
                if len(params_str) > 600:
                    params_str = params_str[:600] + '\n  ...'
                print(f'  Parameters: {params_str}')
                print()
        else:
            print(f'No template configs found for: {args.template_configs}')
        return

    if args.template_search:
        templates = search_templates(args.template_search)
        if templates:
            if args.json:
                print(json.dumps(templates, indent=2, default=str))
            else:
                for t in templates:
                    print(f'[{t["id"]}] {t["name"]} ({t["views"]} views)')
                    if t['description']:
                        print(f'  {t["description"]}')
                    if t['nodes_used']:
                        print(f'  Nodes: {t["nodes_used"][:100]}')
                    print()
                print(f'{len(templates)} templates found')
        else:
            print(f'No templates found for: {args.template_search}')
        return

    if args.query:
        results = search_nodes(
            args.query,
            limit=args.limit,
            triggers_only=args.triggers_only,
            ai_only=args.ai_only,
            core_only=args.core_only,
            no_tool_variants=args.no_tool_variants,
        )
        if args.json:
            out = []
            for score, node_type, row in results:
                out.append({
                    'node_type': node_type,
                    'sdk_type': to_sdk_format(node_type),
                    'display_name': row[1],
                    'description': row[2],
                    'category': row[3],
                    'is_trigger': bool(row[4]),
                    'is_ai_tool': bool(row[5]),
                    'is_tool_variant': bool(row[6]),
                    'score': round(score, 2),
                })
            print(json.dumps(out, indent=2))
        else:
            for score, node_type, row in results:
                sdk_type = to_sdk_format(node_type)
                name = row[1]
                desc = (row[2] or '')[:80]
                version = row[9] or ''
                flags = []
                if row[4]: flags.append('TRIGGER')
                if row[5]: flags.append('AI')
                if row[6]: flags.append('TOOL-VAR')
                if row[7]: flags.append('COMMUNITY')
                if row[8]: flags.append('VERIFIED')
                flags_str = f' [{" ".join(flags)}]' if flags else ''
                print(f'{sdk_type} | {name} v{version}{flags_str} (score: {score:.1f})')
                if desc:
                    print(f'  {desc}')
            print(f'\n{len(results)} results for "{args.query}"')
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
