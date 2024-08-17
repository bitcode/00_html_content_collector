# ./00_html_content_collector/diff_generator.py
import hashlib
from datetime import datetime
import logging
from custom_exceptions import ParsingError, ScraperError
from logger import log_error, log_info

# Initialize logger
logger = logging.getLogger('scraper.diff_generator')

def chunk_content(content, chunk_size=1000):
    """Split content into chunks of specified size."""
    return [content[i:i + chunk_size] for i in range(0, len(content), chunk_size)]

def myers_diff(old_content, new_content):
    try:
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
    except Exception as e:
        raise ParsingError(f"Error in myers_diff: {str(e)}")

def generate_diff(old_content, new_content, doc_name, version):
    try:
        diff = myers_diff(old_content, new_content)

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

        log_info(logger, f"Generated diff for {doc_name} version {version}")
        return formatted_diff
    except Exception as e:
        log_error(logger, ParsingError(f"Error generating diff: {str(e)}", doc_name=doc_name, version=version))
        raise

def generate_optimized_diff(old_content, new_content, doc_name, version, chunk_size=1000):
    try:
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

        log_info(logger, f"Generated optimized diff for {doc_name} version {version}")
        return formatted_diff
    except Exception as e:
        log_error(logger, ParsingError(f"Error generating optimized diff: {str(e)}", doc_name=doc_name, version=version))
        raise

def format_chunk_diff(diff, old_chunk, new_chunk):
    try:
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
    except Exception as e:
        raise ParsingError(f"Error in format_chunk_diff: {str(e)}")


# Example usage
if __name__ == "__main__":
    try:
        old_content = "This is the old content.\nIt has multiple lines.\nSome lines will change."
        new_content = "This is the new content.\nIt has multiple lines.\nSome lines have changed."

        diff = generate_diff(old_content, new_content, "example_doc", "1.0")
        print("Standard diff:", diff)

        optimized_diff = generate_optimized_diff(old_content, new_content, "example_doc", "1.0")
        print("Optimized diff:", optimized_diff)
    except ScraperError as e:
        log_error(logger, e)
    except Exception as e:
        log_error(logger, ScraperError(f"Unexpected error in diff generation: {str(e)}"))
