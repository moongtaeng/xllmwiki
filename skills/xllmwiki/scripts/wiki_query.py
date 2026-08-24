#!/usr/bin/env python3
"""Query the compiled graph. Returns answers, not files.

Standard library only.

    python3 wiki_query.py map                     # routing table, no bodies
    python3 wiki_query.py neighbors kv-cache      # what connects to it
    python3 wiki_query.py facts kv-cache          # typed relations, with evidence
    python3 wiki_query.py path vllm kv-cache      # how two pages connect
    python3 wiki_query.py find quantization       # slug/label/summary search
    python3 wiki_query.py status disputed         # relations by status
    python3 wiki_query.py orphans                 # unreachable / dangling
    python3 wiki_query.py domains                 # inventory + cross-links

Add --json for machine output, --wiki DIR to point elsewhere, --domain NAME to
pick a domain in a multi-domain wiki. With no --wiki, the wiki is found by
walking up from the current directory, so this works from anywhere inside the
project.

Reading whole pages costs ~590 chars each; these answers cost a few hundred
total. That gap is the whole reason the graph exists.
"""
import io
import json
import os
import sys
import unicodedata
from collections import defaultdict, deque

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wiki_paths  # noqa: E402

IMPLICIT = ('mentions', 'sourced_from')


def load(wiki_dir, focus=None):
    """Return (nodes, edges). Transparently reassembles a sharded graph.

    `focus` is a slug the caller cares about. On a sharded wiki that loads
    only its shard plus the cross-shard edges, instead of every shard --
    the point of sharding in the first place. Commands that scan the whole
    wiki (map, find, orphans, status) pass focus=None and take the full read.
    """
    gdir = os.path.join(wiki_dir, 'graph')
    single = os.path.join(gdir, 'graph.json')
    index = os.path.join(gdir, 'index.json')

    if os.path.isfile(single):
        g = read(single)['graph']
        return g.get('nodes', {}), g.get('edges', [])

    if os.path.isfile(index):
        idx = read(index)
        shards = idx.get('shards', [])
        picked = shards
        if focus:
            hit = [s for s in shards if focus in s.get('slugs', [])]
            # An unknown or partial slug needs every shard so resolve() can
            # still match on a substring.
            picked = hit or shards

        nodes, edges = {}, []
        for shard in picked:
            g = read(os.path.join(gdir, shard['file']))['graph']
            nodes.update(g.get('nodes', {}))
            edges.extend(g.get('edges', []))
        cross = os.path.join(gdir, 'cross.json')
        if os.path.isfile(cross):
            edges.extend(read(cross).get('edges', []))

        # Pages in shards we skipped still exist -- record them as stubs so a
        # neighbour in another shard is not reported as "not written yet".
        if len(picked) != len(shards):
            for s in shards:
                if s in picked:
                    continue
                for slug in s.get('slugs', []):
                    nodes.setdefault(slug, {'label': slug, 'metadata': {
                        'type': '', 'tags': [], 'file': '',
                        'summary': '', 'shard': s['id']}})
        return nodes, edges

    die('no compiled graph in %s -- run wiki_graph.py first' % gdir)


def read(path):
    with io.open(path, encoding='utf-8') as f:
        return json.load(f)


def die(msg):
    sys.stderr.write(msg + '\n')
    sys.exit(2)


def norm(s):
    """Fold for matching: NFC so Hangul jamo compares equal regardless of how
    the filesystem or editor encoded it, casefold for scripts that have case.
    CJK is caseless, so casefold is a no-op there and costs nothing."""
    return unicodedata.normalize('NFC', s).casefold()


def resolve(nodes, name):
    """Exact slug, else unique substring match. Script-agnostic."""
    if name in nodes:
        return name
    target = norm(name)
    exact = [s for s in nodes if norm(s) == target]
    if exact:
        return exact[0]
    hits = [s for s in nodes if target in norm(s)]
    if len(hits) == 1:
        return hits[0]
    if not hits:
        die('no page matching %r' % name)
    die('ambiguous %r -- matches: %s' % (name, ', '.join(sorted(hits)[:8])))


# --- commands -------------------------------------------------------------

def cmd_map(nodes, edges, args):
    """Routing table: every page as type + one-line summary. No bodies."""
    by_type = defaultdict(list)
    for slug, n in nodes.items():
        by_type[n['metadata'].get('type') or '?'].append(slug)
    out = []
    for t in sorted(by_type):
        out.append({'type': t, 'pages': [
            {'slug': s, 'summary': nodes[s]['metadata'].get('summary', '')}
            for s in sorted(by_type[t])]})
    return out


def cmd_neighbors(nodes, edges, args):
    if not args:
        die('usage: neighbors <slug>')
    slug = resolve(nodes, args[0])
    seen = []
    for e in edges:
        if e['source'] == slug:
            seen.append({'dir': '->', 'relation': e['relation'],
                         'other': e['target'],
                         'summary': summary(nodes, e['target'])})
        elif e['target'] == slug:
            seen.append({'dir': '<-', 'relation': e['relation'],
                         'other': e['source'],
                         'summary': summary(nodes, e['source'])})
    return {'node': slug, 'summary': summary(nodes, slug), 'edges': seen}


def cmd_facts(nodes, edges, args):
    """Typed relations only -- the claims someone actually sourced."""
    if not args:
        die('usage: facts <slug>')
    slug = resolve(nodes, args[0])
    facts = []
    for e in edges:
        if e['relation'] in IMPLICIT:
            continue
        if slug not in (e['source'], e['target']):
            continue
        md = e.get('metadata') or {}
        facts.append({
            'subject': e['source'], 'predicate': e['relation'],
            'object': e['target'], 'source': md.get('source', ''),
            'evidence': md.get('evidence', ''),
            'status': md.get('status', 'current'),
        })
    return {'node': slug, 'facts': facts}


def cmd_path(nodes, edges, args):
    if len(args) < 2:
        die('usage: path <from> <to>')
    a, b = resolve(nodes, args[0]), resolve(nodes, args[1])
    # Routing through a shared raw file is not a meaningful connection --
    # it would make every pair of pages citing one paper "2 hops apart".
    adj = defaultdict(list)
    for e in edges:
        if is_raw(e['source']) or is_raw(e['target']):
            continue
        adj[e['source']].append((e['target'], e['relation']))
        adj[e['target']].append((e['source'], e['relation']))
    prev, q = {a: None}, deque([a])
    while q:
        cur = q.popleft()
        if cur == b:
            break
        for nxt, rel in adj[cur]:
            if nxt not in prev:
                prev[nxt] = (cur, rel)
                q.append(nxt)
    if b not in prev:
        return {'from': a, 'to': b, 'path': None}
    chain, cur = [], b
    while prev[cur] is not None:
        parent, rel = prev[cur]
        chain.append({'from': parent, 'relation': rel, 'to': cur})
        cur = parent
    return {'from': a, 'to': b, 'hops': len(chain),
            'path': list(reversed(chain))}


def cmd_find(nodes, edges, args):
    if not args:
        die('usage: find <term>')
    term = norm(' '.join(args))
    hits = []
    for slug, n in sorted(nodes.items()):
        md = n['metadata']
        hay = norm(' '.join([slug, n.get('label', ''), md.get('summary', ''),
                             ' '.join(md.get('tags', []))]))
        if term in hay:
            hits.append({'slug': slug, 'type': md.get('type', ''),
                         'summary': md.get('summary', '')})
    return {'term': term, 'hits': hits}


def cmd_status(nodes, edges, args):
    """Relations by status -- 'disputed' and 'superseded' are the interesting ones."""
    want = args[0] if args else None
    rows = []
    for e in edges:
        if e['relation'] in IMPLICIT:
            continue
        md = e.get('metadata') or {}
        st = md.get('status', 'current')
        if want and st != want:
            continue
        rows.append({'subject': e['source'], 'predicate': e['relation'],
                     'object': e['target'], 'status': st,
                     'source': md.get('source', ''),
                     'evidence': md.get('evidence', '')})
    return {'status': want or 'all', 'relations': rows}


def cmd_orphans(nodes, edges, args):
    """Pages nothing links to, and links pointing at pages that don't exist."""
    # A typed relation is a stronger inbound link than a [[wikilink]], so a
    # page reached only that way is not an orphan.
    linked = set()
    for e in edges:
        if e['relation'] != 'sourced_from':
            linked.add(e['target'])
    dangling = defaultdict(list)
    for e in edges:
        if e['relation'] == 'mentions' and e['target'] not in nodes:
            dangling[e['target']].append(e['source'])
    return {
        'unlinked': sorted(s for s in nodes if s not in linked),
        'dangling': [{'slug': k, 'referenced_by': sorted(v), 'count': len(v)}
                     for k, v in sorted(dangling.items(),
                                        key=lambda kv: -len(kv[1]))],
    }


def is_raw(slug):
    """raw/ targets are source files, not pages -- they end paths, not extend them."""
    return slug.startswith('raw/')


def summary(nodes, slug):
    n = nodes.get(slug)
    if n:
        s = n['metadata'].get('summary', '')
        if s:
            return s
        shard = n['metadata'].get('shard')
        return '(in shard: %s)' % shard if shard else ''
    return '(raw source)' if is_raw(slug) else '(page not written yet)'


def list_domains(root):
    """Inventory a multi-domain wiki, plus which links cross domain borders.

    Cross-domain links are allowed -- knowledge does not respect the folder it
    was filed in -- so they are reported, not flagged.
    """
    cfg = wiki_paths.read_config(root)
    names = wiki_paths.domains(root, cfg)
    if not names:
        return {'root': root, 'single': True, 'domains': []}

    owner, rows = {}, []
    for name in names:
        wiki_dir, _raw = wiki_paths.domain_paths(root, name, cfg)
        gdir = os.path.join(wiki_dir, 'graph')
        compiled = (os.path.isfile(os.path.join(gdir, 'graph.json'))
                    or os.path.isfile(os.path.join(gdir, 'index.json')))
        pages = []
        if compiled:
            nodes, edges = load(wiki_dir)
            pages = sorted(nodes)
            for slug in pages:
                owner[slug] = name
        rows.append({'name': name, 'compiled': compiled,
                     'pages': len(pages),
                     'dir': wiki_paths.rel(wiki_dir, root)})

    crossing = []
    for row in rows:
        if not row['compiled']:
            continue
        wiki_dir, _raw = wiki_paths.domain_paths(root, row['name'], cfg)
        _nodes, edges = load(wiki_dir)
        for e in edges:
            if e['relation'] == 'sourced_from':
                continue
            there = owner.get(e['target'])
            if there and there != row['name']:
                crossing.append({'from_domain': row['name'],
                                 'to_domain': there,
                                 'source': e['source'], 'target': e['target'],
                                 'relation': e['relation']})
    return {'root': root, 'single': False, 'domains': rows,
            'crossing': crossing}


COMMANDS = {'map': cmd_map, 'neighbors': cmd_neighbors, 'facts': cmd_facts,
            'path': cmd_path, 'find': cmd_find, 'status': cmd_status,
            'orphans': cmd_orphans}


# --- rendering ------------------------------------------------------------

def width(s):
    """Display columns, counting CJK/fullwidth characters as two."""
    return sum(2 if unicodedata.east_asian_width(c) in 'WF' else 1 for c in s)


def clip(s, cols):
    """Trim to a column budget, not a character count -- CJK is double-width."""
    if width(s) <= cols:
        return s
    if cols <= 1:
        return s[:1] if cols == 1 else ''
    out, used = [], 0
    for c in s:
        w = 2 if unicodedata.east_asian_width(c) in 'WF' else 1
        if used + w > cols - 1:
            break
        out.append(c)
        used += w
    return ''.join(out) + '…'


def render(cmd, data):
    """Plain text, deliberately compact -- this output lands in a context window."""
    if cmd == 'map':
        for group in data:
            print('[%s]' % group['type'])
            for p in group['pages']:
                print('  %-28s %s' % (p['slug'], clip(p['summary'], 60)))
        return
    if cmd == 'neighbors':
        print('%s -- %s' % (data['node'], clip(data['summary'], 70)))
        for e in data['edges']:
            print('  %s %-14s %-26s %s' % (e['dir'], e['relation'],
                                           e['other'], clip(e['summary'], 50)))
        if not data['edges']:
            print('  (no edges)')
        return
    if cmd == 'facts':
        if not data['facts']:
            print('%s: no typed relations' % data['node'])
            return
        for f in data['facts']:
            print('%s %s %s  [%s]' % (f['subject'], f['predicate'],
                                      f['object'], f['status']))
            if f['evidence']:
                print('    "%s"' % f['evidence'])
            if f['source']:
                print('    source: %s' % f['source'])
        return
    if cmd == 'path':
        if data['path'] is None:
            print('no path: %s -> %s' % (data['from'], data['to']))
            return
        if not data['path']:
            print('%s is the same page' % data['from'])
            return
        print('%s -> %s (%d hops)' % (data['from'], data['to'], data['hops']))
        for h in data['path']:
            print('  %s --%s--> %s' % (h['from'], h['relation'], h['to']))
        return
    if cmd == 'find':
        if not data['hits']:
            print('no match: %s' % data['term'])
            return
        for h in data['hits']:
            print('%-28s %-10s %s' % (h['slug'], h['type'],
                                      clip(h['summary'], 55)))
        return
    if cmd == 'status':
        if not data['relations']:
            print('no relations with status=%s' % data['status'])
            return
        for r in data['relations']:
            print('%s %s %s  [%s]' % (r['subject'], r['predicate'],
                                      r['object'], r['status']))
            if r['evidence']:
                print('    "%s"' % r['evidence'])
        return
    if cmd == 'domains':
        if data['single']:
            print('single-domain wiki at %s' % data['root'])
            return
        for d in data['domains']:
            state = '%d pages' % d['pages'] if d['compiled'] else 'not compiled'
            print('%-20s %-14s %s' % (d['name'], state, d['dir']))
        cross = data['crossing']
        print('\ncross-domain links: %d' % len(cross))
        for c in cross[:15]:
            print('  %s/%s --%s--> %s/%s'
                  % (c['from_domain'], c['source'], c['relation'],
                     c['to_domain'], c['target']))
        if len(cross) > 15:
            print('  ... and %d more' % (len(cross) - 15))
        return
    if cmd == 'orphans':
        print('unlinked pages: %d' % len(data['unlinked']))
        for s in data['unlinked']:
            print('  %s' % s)
        print('dangling links: %d' % len(data['dangling']))
        for d in data['dangling']:
            print('  [[%s]] <- %d page(s): %s'
                  % (d['slug'], d['count'], ', '.join(d['referenced_by'][:4])))


def main(argv):
    args = [a for a in argv[1:]]
    as_json = '--json' in args
    args = [a for a in args if a != '--json']
    explicit, domain = None, None
    for flag in ('--wiki', '--domain'):
        while flag in args:
            i = args.index(flag)
            if i + 1 >= len(args):
                die('%s needs a value' % flag)
            if flag == '--wiki':
                explicit = args[i + 1]
            else:
                domain = args[i + 1]
            del args[i:i + 2]

    if not args or args[0] in ('-h', '--help'):
        print(__doc__.strip())
        return 0
    cmd = args[0]
    if cmd not in COMMANDS and cmd != 'domains':
        die('unknown command %r -- one of: %s'
            % (cmd, ', '.join(sorted(list(COMMANDS) + ['domains']))))

    if cmd == 'domains':
        root = wiki_paths.find_root(explicit or None)
        if root is None:
            die('no wiki found here or in any parent directory.')
        data = list_domains(root)
        if as_json:
            json.dump(data, sys.stdout, ensure_ascii=False, indent=1)
            print()
        else:
            render('domains', data)
        return 0

    wiki_dir, _raw, root, name = wiki_paths.resolve(explicit, domain)
    if wiki_dir is None:
        if root is None:
            die('no wiki found here or in any parent directory.\n'
                'run wiki_init.py to create one, or pass --wiki DIR.')
        avail = wiki_paths.domains(root)
        if domain and name == domain:
            die('no domain %r. domains: %s' % (domain, ', '.join(avail)))
        die('this wiki has several domains; pick one with --domain NAME.\n'
            'domains: %s' % (', '.join(avail) or '(none yet)'))

    # Single-node commands only need that node's shard; the rest scan everything.
    focus = args[1] if cmd in ('neighbors', 'facts') and len(args) > 1 else None
    nodes, edges = load(wiki_dir, focus)
    data = COMMANDS[cmd](nodes, edges, args[1:])
    if as_json:
        json.dump(data, sys.stdout, ensure_ascii=False, indent=1)
        print()
    else:
        render(cmd, data)
    return 0


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    sys.exit(main(sys.argv))
