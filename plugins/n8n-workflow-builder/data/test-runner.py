#!/usr/bin/env python3
"""
n8n Workflow Test Runner — Save, load, and compare test cases for workflow testing.

Usage:
    python3 test-runner.py --save <workflowId> <test_json>   Save a test case
    python3 test-runner.py --load <workflowId>                Load all test cases
    python3 test-runner.py --list                             List all test suites
    python3 test-runner.py --compare <actual> <expected>       Compare actual vs expected
    python3 test-runner.py --delete <workflowId> [test_name]  Delete test(s)
"""

import json
import sys
import os
import io
import argparse
import re
from datetime import datetime

# Force UTF-8 output on Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if sys.stderr.encoding != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

TESTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tests')


def ensure_tests_dir():
    os.makedirs(TESTS_DIR, exist_ok=True)


def get_test_file(workflow_id):
    return os.path.join(TESTS_DIR, f'{workflow_id}.json')


def save_test(workflow_id, test_json_str):
    """Save a test case to the test suite file."""
    ensure_tests_dir()
    filepath = get_test_file(workflow_id)

    # Load existing suite or create new
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            suite = json.load(f)
    else:
        suite = {
            'workflowId': workflow_id,
            'testCases': [],
            'lastRun': None,
            'lastResult': None
        }

    # Parse the new test case
    test_case = json.loads(test_json_str)

    # Check for duplicate name
    existing_names = [tc.get('name', '') for tc in suite['testCases']]
    if test_case.get('name', '') in existing_names:
        # Replace existing test with same name
        suite['testCases'] = [
            tc for tc in suite['testCases']
            if tc.get('name', '') != test_case.get('name', '')
        ]

    suite['testCases'].append(test_case)

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(suite, f, indent=2, ensure_ascii=False)

    print(f'Saved test "{test_case.get("name", "unnamed")}" for workflow {workflow_id}')
    print(f'Total tests: {len(suite["testCases"])}')


def load_tests(workflow_id):
    """Load all test cases for a workflow."""
    filepath = get_test_file(workflow_id)
    if not os.path.exists(filepath):
        print(f'No test suite found for workflow {workflow_id}')
        return

    with open(filepath, 'r', encoding='utf-8') as f:
        suite = json.load(f)

    print(json.dumps(suite, indent=2, ensure_ascii=False))


def list_suites():
    """List all test suites."""
    ensure_tests_dir()
    files = [f for f in os.listdir(TESTS_DIR) if f.endswith('.json')]

    if not files:
        print('No test suites saved yet.')
        return

    for f in sorted(files):
        filepath = os.path.join(TESTS_DIR, f)
        with open(filepath, 'r', encoding='utf-8') as fh:
            suite = json.load(fh)
        wf_id = suite.get('workflowId', f.replace('.json', ''))
        wf_name = suite.get('workflowName', 'Unknown')
        count = len(suite.get('testCases', []))
        last_run = suite.get('lastRun', 'Never')
        last_result = suite.get('lastResult', {})
        passed = last_result.get('passed', '?')
        total = last_result.get('total', '?')
        print(f'{wf_id} | {wf_name} | {count} tests | Last run: {last_run} | {passed}/{total} passed')


def compare(actual_json_str, expected_json_str):
    """Compare actual execution output against expected."""
    actual = json.loads(actual_json_str)
    expected = json.loads(expected_json_str)
    diffs = []

    # Check overall status
    if 'status' in expected:
        if actual.get('status') != expected['status']:
            diffs.append({
                'type': 'status_mismatch',
                'field': 'execution.status',
                'expected': expected['status'],
                'actual': actual.get('status', 'unknown')
            })

    # Check per-node assertions
    node_checks = expected.get('nodeChecks', {})
    actual_nodes = actual.get('nodes', {})

    for node_name, checks in node_checks.items():
        node_data = actual_nodes.get(node_name, {})

        # Status check
        if 'status' in checks:
            node_status = node_data.get('status', 'unknown')
            if node_status != checks['status']:
                diffs.append({
                    'type': 'node_status_mismatch',
                    'node': node_name,
                    'expected': checks['status'],
                    'actual': node_status
                })

        # outputContains check (partial match)
        if 'outputContains' in checks:
            node_output = node_data.get('output', {})
            for key, expected_val in checks['outputContains'].items():
                actual_val = node_output.get(key)
                if actual_val != expected_val:
                    diffs.append({
                        'type': 'output_mismatch',
                        'node': node_name,
                        'field': key,
                        'expected': expected_val,
                        'actual': actual_val
                    })

        # outputEquals check (exact match)
        if 'outputEquals' in checks:
            node_output = node_data.get('output', {})
            if node_output != checks['outputEquals']:
                diffs.append({
                    'type': 'output_not_equal',
                    'node': node_name,
                    'expected': checks['outputEquals'],
                    'actual': node_output
                })

        # outputMatches check (regex)
        if 'outputMatches' in checks:
            node_output = node_data.get('output', {})
            for key, pattern in checks['outputMatches'].items():
                actual_val = str(node_output.get(key, ''))
                if not re.search(pattern, actual_val):
                    diffs.append({
                        'type': 'regex_mismatch',
                        'node': node_name,
                        'field': key,
                        'pattern': pattern,
                        'actual': actual_val
                    })

    # Output result
    if not diffs:
        print('PASS — All checks matched')
    else:
        print(f'FAIL — {len(diffs)} mismatches:')
        for d in diffs:
            if d['type'] == 'status_mismatch':
                print(f'  Status: expected "{d["expected"]}", got "{d["actual"]}"')
            elif d['type'] == 'node_status_mismatch':
                print(f'  Node "{d["node"]}": expected status "{d["expected"]}", got "{d["actual"]}"')
            elif d['type'] == 'output_mismatch':
                print(f'  Node "{d["node"]}" field "{d["field"]}": expected {d["expected"]}, got {d["actual"]}')
            elif d['type'] == 'output_not_equal':
                print(f'  Node "{d["node"]}": output does not match expected')
            elif d['type'] == 'regex_mismatch':
                print(f'  Node "{d["node"]}" field "{d["field"]}": does not match pattern "{d["pattern"]}"')

    return diffs


def delete_tests(workflow_id, test_name=None):
    """Delete a test case or entire suite."""
    filepath = get_test_file(workflow_id)
    if not os.path.exists(filepath):
        print(f'No test suite found for workflow {workflow_id}')
        return

    if test_name:
        with open(filepath, 'r', encoding='utf-8') as f:
            suite = json.load(f)
        before = len(suite['testCases'])
        suite['testCases'] = [tc for tc in suite['testCases'] if tc.get('name', '') != test_name]
        after = len(suite['testCases'])
        if before == after:
            print(f'Test "{test_name}" not found')
        else:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(suite, f, indent=2, ensure_ascii=False)
            print(f'Deleted test "{test_name}". Remaining: {after}')
    else:
        os.remove(filepath)
        print(f'Deleted entire test suite for workflow {workflow_id}')


def main():
    parser = argparse.ArgumentParser(description='n8n Workflow Test Runner')
    parser.add_argument('--save', nargs=2, metavar=('WORKFLOW_ID', 'TEST_JSON'), help='Save a test case')
    parser.add_argument('--load', metavar='WORKFLOW_ID', help='Load test cases for a workflow')
    parser.add_argument('--list', action='store_true', help='List all test suites')
    parser.add_argument('--compare', nargs=2, metavar=('ACTUAL', 'EXPECTED'), help='Compare actual vs expected JSON')
    parser.add_argument('--delete', nargs='+', metavar=('WORKFLOW_ID', 'TEST_NAME'), help='Delete test(s)')
    args = parser.parse_args()

    if args.save:
        save_test(args.save[0], args.save[1])
    elif args.load:
        load_tests(args.load)
    elif args.list:
        list_suites()
    elif args.compare:
        compare(args.compare[0], args.compare[1])
    elif args.delete:
        wf_id = args.delete[0]
        test_name = args.delete[1] if len(args.delete) > 1 else None
        delete_tests(wf_id, test_name)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
