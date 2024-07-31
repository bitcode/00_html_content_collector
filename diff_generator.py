import hashlib
from scraper import chunk_content
import datetime

def myers_diff(old_content, new_content):
    def shortest_edit_sequence(a, b):
        n, m = len(a), len(b)
        max_d = n + m
        v = {1: 0}
        trace = []

        for d in range(max_d + 1):
            for k in range(-d, d + 1, 2):
                if k == -d or (k != d and v.get(k - 1, float('-inf')) < v.get(k + 1, float('-inf'))):
                    x = v[k + 1]
                else:
                    x = v[k - 1] + 1
                y = x - k
                while x < n and y < m and a[x] == b[y]:
                    x, y = x + 1, y + 1
                v[k] = x
                if x >= n and y >= m:
                    return trace
            trace.append(v.copy())
        return trace

    def backtrack(trace, a, b):
        x, y = len(a), len(b)
        path = []
        for d, v in reversed(list(enumerate(trace))):
            k = x - y
            if k == -d or (k != d and v.get(k - 1, float('-inf')) < v.get(k + 1, float('-inf'))):
                k = k + 1
            prev_x, prev_y = v[k], v[k] - k
            while x > prev_x and y > prev_y:
                path.append(('equal', x - 1, y - 1))
                x, y = x - 1, y - 1
            if d > 0:
                path.append(('replace' if x > prev_x else 'insert', prev_x, prev_y))
            x, y = prev_x, prev_y
        return list(reversed(path))

    a, b = old_content.splitlines(), new_content.splitlines()
    trace = shortest_edit_sequence(a, b)
    return backtrack(trace, a, b)

def generate_diff(old_content, new_content, doc_name, version):
    diff = myers_diff(old_content, new_content)

    # Create a custom diff format with metadata
    formatted_diff = {
        'metadata': {
            'doc_name': doc_name,
            'version': version,
            'timestamp': datetime.now().isoformat(),
            'old_content_hash': hashlib.md5(old_content.encode()).hexdigest(),
            'new_content_hash': hashlib.md5(new_content.encode()).hexdigest(),
        },
        'operations': []
    }

    for op, old_pos, new_pos in diff:
        if op == 'equal':
            formatted_diff['operations'].append({
                'operation': 'equal',
                'content': old_content.splitlines()[old_pos]
            })
        elif op == 'replace':
            formatted_diff['operations'].append({
                'operation': 'replace',
                'old_content': old_content.splitlines()[old_pos],
                'new_content': new_content.splitlines()[new_pos]
            })
        elif op == 'insert':
            formatted_diff['operations'].append({
                'operation': 'insert',
                'content': new_content.splitlines()[new_pos]
            })
        elif op == 'delete':
            formatted_diff['operations'].append({
                'operation': 'delete',
                'content': old_content.splitlines()[old_pos]
            })

    return formatted_diff

def generate_optimized_diff(old_content, new_content, doc_name, version, chunk_size=1000):
    old_chunks = chunk_content(old_content, chunk_size)
    new_chunks = chunk_content(new_content, chunk_size)

    formatted_diff = {
        'metadata': {
            'doc_name': doc_name,
            'version': version,
            'timestamp': datetime.now().isoformat(),
            'old_content_hash': hashlib.md5(old_content.encode()).hexdigest(),
            'new_content_hash': hashlib.md5(new_content.encode()).hexdigest(),
        },
        'chunks': []
    }

    for i, (old_chunk, new_chunk) in enumerate(zip(old_chunks, new_chunks)):
        if old_chunk != new_chunk:
            chunk_diff = myers_diff(old_chunk, new_chunk)
            formatted_diff['chunks'].append({
                'chunk_index': i,
                'operations': format_chunk_diff(chunk_diff, old_chunk, new_chunk)
            })

    # Handle case where new content has more chunks
    for i, new_chunk in enumerate(new_chunks[len(old_chunks):], start=len(old_chunks)):
        formatted_diff['chunks'].append({
            'chunk_index': i,
            'operations': [{'operation': 'insert', 'content': new_chunk}]
        })

    return formatted_diff

def format_chunk_diff(diff, old_chunk, new_chunk):
    formatted_ops = []
    for op, old_pos, new_pos in diff:
        if op == 'equal':
            formatted_ops.append({
                'operation': 'equal',
                'content': old_chunk[old_pos]
            })
        elif op == 'replace':
            formatted_ops.append({
                'operation': 'replace',
                'old_content': old_chunk[old_pos],
                'new_content': new_chunk[new_pos]
            })
        elif op == 'insert':
            formatted_ops.append({
                'operation': 'insert',
                'content': new_chunk[new_pos]
            })
        elif op == 'delete':
            formatted_ops.append({
                'operation': 'delete',
                'content': old_chunk[old_pos]
            })
    return formatted_ops
