#!/usr/bin/env python3
"""Compile the markdown wiki into a JSON Graph Format v2 index.

Standard library only. No uv, no pyyaml, no networkx.

    python3 wiki_graph.py [root] [--domain NAME] [--all]

With no argument, finds the wiki by walking up from the current directory
looking for .xllmwiki, so it works from anywhere
inside the project. In a multi-domain wiki the domain containing the current
directory is used; --domain picks one explicitly and --all compiles every one.

Writes <wiki>/graph/graph.json, or a sharded set when the wiki outgrows one
file (see SHARD_THRESHOLD). Markdown stays canonical; everything here is
regenerable and safe to delete.
"""
import glob
import hashlib
import io
import json
import os
import re
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wiki_paths  # noqa: E402

# Above this many pages, one graph.json costs more context than it saves.
# Measured: ~98 chars/page of routing data, so 200 pages is ~9k tokens.
SHARD_THRESHOLD = 200

# ponytail: hand-rolled block-YAML reader. Frontmatter here is a closed
# format (page-format.md), so a real parser would be a dependency for
# nothing. Swap in pyyaml only if the format grows nested structures.


def parse_frontmatter(text):
    """Return (fields, body). Handles scalars, block lists, and relations."""
    m = re.match(r'^---\n(.*?)\n---\n', text, re.S)
    if not m:
        return {}, text
    raw, body = m.group(1), text[m.end():]
    out, key = {}, None
    for line in raw.split('\n'):
        # Any top-level key, not just lowercase ASCII: an unrecognised key
        # must still close the open block list, or its items get merged into
        # the previous field and quietly corrupt tags.
        if re.match(r'^\S.*?:', line):
            k, _, v = line.partition(':')
            k, v = k.strip(), v.strip()
            if v:
                out[k] = v.strip('"\'')
                key = None
            else:
                out[k] = []
                key = k
        elif line.startswith('  - ') and key:
            out[key].append(line[4:].strip().strip('"\''))
    out['relations'] = parse_relations(raw)
    return out, body


def parse_relations(raw):
    """Parse the optional relations block.

        relations:
          - depends_on: kv-cache
            source: src-vllm-2023
            evidence: "quoted snippet"
            status: current
    """
    block = re.search(r'^relations:\n((?:  [-\s].*\n?)*)', raw, re.M)
    if not block:
        return []
    rels, cur = [], None
    for line in block.group(1).split('\n'):
        # Predicates are free-form per page-format.md, so accept hyphens and
        # non-ASCII. An empty object is kept (not dropped) so validation can
        # report the half-finished edit instead of losing it.
        item = re.match(r'^  - ([^\s:]+):\s*(.*)$', line)
        if item:
            if cur:
                rels.append(cur)
            cur = {'predicate': item.group(1),
                   'object': item.group(2).strip().strip('"\'')}
            continue
        field = re.match(r'^    ([^\s:]+):\s*(.*)$', line)
        if field and cur is not None:
            cur[field.group(1)] = field.group(2).strip().strip('"\'')
    if cur:
        rels.append(cur)
    return rels


def strip_markup(text):
    """Drop markup that wastes the summary budget and pollutes `find` matches.

    page-format.md mandates footnote citations on the opening paragraph, so
    nearly every page would otherwise spend characters on a [^ref] marker and
    show link syntax to the reader.
    """
    text = re.sub(r'\[\^[^\]]*\]', '', text)          # footnote markers
    text = re.sub(r'\[\[([^\]|]*\|)?([^\]]*)\]\]', r'\2', text)  # wikilinks
    text = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', text)         # md links
    text = re.sub(r'[`*_]+', '', text)                # emphasis / code ticks
    return text


def first_sentence(body, cols=110):
    """The opening paragraph is the page in miniature -- use it as summary.

    Budget is display columns, not characters: CJK is double-width, so 110
    chars of Korean or Japanese carries roughly twice the payload of Latin
    text and would bloat every routing query.
    """
    for p in body.split('\n\n'):
        p = p.strip()
        if not p or p.startswith('#'):
            continue
        flat = ' '.join(strip_markup(p).split())
        out, used = [], 0
        for c in flat:
            w = 2 if unicodedata.east_asian_width(c) in 'WF' else 1
            if used + w > cols:
                break
            out.append(c)
            used += w
        return ''.join(out)
    return ''


def slug_of(path):
    return os.path.splitext(os.path.basename(path))[0]


def is_raw(target):
    """raw/ targets are source files, not pages -- they have no node."""
    return target.startswith('raw/')


def build(wiki_dir, root):
    """Read every page; return (nodes, edges, problems).

    `root` is the wiki root -- recorded paths are relative to it so the graph
    stays portable no matter where the compile was run from.
    """
    nodes, edges, problems = {}, [], []

    for slug, paths in sorted(wiki_paths.duplicate_slugs(wiki_dir).items()):
        problems.append('duplicate slug %r in: %s'
                        % (slug, ', '.join(wiki_paths.rel(p, root)
                                           for p in paths)))

    for path in wiki_paths.page_files(wiki_dir):
        text = io.open(path, encoding='utf-8').read()
        fm, body = parse_frontmatter(text)
        holder = os.path.basename(os.path.dirname(path))
        declared = fm.get('type', '')
        # The directory mirrors `type:`; frontmatter is authoritative. Report
        # the mismatch rather than moving the file -- a silent move is how a
        # link breaks without anyone noticing.
        if (declared and holder in wiki_paths.PAGE_TYPES
                and declared != holder):
            problems.append('type mismatch: %s declares %s but sits in %s/'
                            % (wiki_paths.rel(path, root), declared, holder))
        # The filename is the addressable identity -- [[wikilinks]] resolve
        # against it. Honouring a divergent declared slug would make every
        # link to this page dangle, so the filename wins and the mismatch is
        # reported for the author to fix.
        slug = slug_of(path)

        if fm.get('slug') and fm['slug'] != slug:
            problems.append('slug mismatch: %s declares %s (using %s from '
                            'the filename)'
                            % (wiki_paths.rel(path, root), fm['slug'], slug))
        if not fm.get('type'):
            problems.append('missing type: %s' % wiki_paths.rel(path, root))

        nodes[slug] = {
            'label': fm.get('title', slug),
            'metadata': {
                'type': fm.get('type', ''),
                'tags': fm.get('tags', []),
                'file': wiki_paths.rel(path, root),
                'updated': fm.get('updated', ''),
                'summary': first_sentence(body),
            },
        }

        for src in fm.get('sources', []):
            edges.append({'source': slug, 'target': src,
                          'relation': 'sourced_from'})

        for link in sorted(set(re.findall(r'\[\[([^\]]+)\]\]', body))):
            edges.append({'source': slug, 'target': link,
                          'relation': 'mentions'})

        for r in fm.get('relations', []):
            missing = [f for f in ('object', 'source', 'evidence')
                       if not r.get(f)]
            if missing:
                problems.append('relation %s->%s in %s missing: %s'
                                % (r['predicate'], r['object'] or '?',
                                   wiki_paths.rel(path, root), ', '.join(missing)))
            if not r.get('object'):
                continue  # nothing to point an edge at
            edges.append({
                'source': slug,
                'target': r['object'],
                'relation': r['predicate'],
                'metadata': {k: v for k, v in r.items()
                             if k not in ('predicate', 'object')} or None,
            })

    for e in edges:
        if 'metadata' in e and e['metadata'] is None:
            del e['metadata']

    return nodes, edges, problems


def shard_key(node):
    """Shard by first tag, falling back to type. Keeps related pages together."""
    tags = node['metadata'].get('tags') or []
    return (tags[0] if tags else node['metadata'].get('type')) or 'misc'


def clear_output(out_dir):
    """Remove previously generated graph files. Only ever deletes the .json
    files this script writes, so a stray file in graph/ survives."""
    for name in ('graph.json', 'index.json', 'cross.json'):
        p = os.path.join(out_dir, name)
        if os.path.isfile(p):
            os.remove(p)
    shard_dir = os.path.join(out_dir, 'shards')
    if os.path.isdir(shard_dir):
        for f in glob.glob(os.path.join(shard_dir, '*.json')):
            os.remove(f)
        if not os.listdir(shard_dir):
            os.rmdir(shard_dir)


def write_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with io.open(path, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, separators=(',', ':'))
    return os.path.getsize(path)


def emit_single(out_dir, nodes, edges):
    path = os.path.join(out_dir, 'graph.json')
    size = write_json(path, {'graph': {'directed': True, 'nodes': nodes,
                                       'edges': edges}})
    return [(path, size)]


def emit_sharded(out_dir, nodes, edges):
    """One file per shard, plus a router index and the cross-shard edges."""
    groups = {}
    for slug, node in nodes.items():
        groups.setdefault(shard_key(node), {})[slug] = node
    home = {slug: k for k, g in groups.items() for slug in g}

    written = []
    inner = {k: [] for k in groups}
    cross = []
    for e in edges:
        a, b = home.get(e['source']), home.get(e['target'])
        if a and a == b:
            inner[a].append(e)
        else:
            cross.append(e)

    # Two different tags can fold to the same filename (case, or punctuation
    # that safe() replaces). Disambiguate rather than silently overwrite.
    filenames, taken = {}, set()
    for k in sorted(groups):
        base = safe(k)
        name = base
        n = 2
        while name in taken:
            name = '%s-%d' % (base, n)
            n += 1
        taken.add(name)
        filenames[k] = name

    for k, g in sorted(groups.items()):
        path = os.path.join(out_dir, 'shards', '%s.json' % filenames[k])
        written.append((path, write_json(path, {
            'graph': {'id': k, 'directed': True, 'nodes': g,
                      'edges': inner[k]}})))

    path = os.path.join(out_dir, 'cross.json')
    written.append((path, write_json(path, {'edges': cross})))

    # The router: shard names, sizes, and which slugs live where. Load this
    # first, then pull only the shards a question actually needs.
    idx = {
        'sharded': True,
        'threshold': SHARD_THRESHOLD,
        'shards': [{'id': k, 'file': 'shards/%s.json' % filenames[k],
                    'pages': len(g),
                    'slugs': sorted(g)} for k, g in sorted(groups.items())],
        'cross_edges': len(cross),
    }
    path = os.path.join(out_dir, 'index.json')
    written.insert(0, (path, write_json(path, idx)))
    return written


def safe(name):
    """Filesystem-safe shard name that survives non-Latin tags.

    Stripping to [a-z0-9] would collapse every Hangul/CJK/Cyrillic tag to the
    same empty string, so all shards would land in one file. Keep any letter or
    digit in any script and drop only what filesystems object to.
    """
    kept = []
    for c in unicodedata.normalize('NFC', name):
        if c.isalnum() or c in '._-':
            kept.append(c.lower())
        else:
            kept.append('-')
    out = re.sub(r'-{2,}', '-', ''.join(kept)).strip('-.')
    # A tag of pure punctuation, or one that collides after folding, still
    # needs a stable filename.
    return out or 'shard-%s' % hashlib.sha1(
        name.encode('utf-8')).hexdigest()[:8]


def main(argv):
    args = argv[1:]
    domain = None
    if '--domain' in args:
        i = args.index('--domain')
        if i + 1 >= len(args):
            sys.stderr.write('--domain needs a name\n')
            return 2
        domain = args[i + 1]
        del args[i:i + 2]
    all_domains = '--all' in args
    args = [a for a in args if a != '--all']
    arg = args[0] if args else None

    root = wiki_paths.find_root(arg or None)
    if root and all_domains:
        return compile_all(root)

    wiki_dir, _raw, root, name = wiki_paths.resolve(arg, domain)
    if wiki_dir is None:
        return report_unresolved(root, name, domain)
    if not os.path.isdir(wiki_dir):
        sys.stderr.write('no %s -- not a wiki\n'
                         % wiki_paths.rel(wiki_dir, root))
        return 2
    if name:
        print('domain: %s' % name)
    # Know the sibling domains' slugs so their links read as cross-domain
    # rather than as pages nobody has written.
    elsewhere = {}
    for other in wiki_paths.domains(root):
        if other == name:
            continue
        w, _r = wiki_paths.domain_paths(root, other)
        for p in wiki_paths.page_files(w):
            elsewhere[slug_of(p)] = other
    return compile_one(wiki_dir, root, elsewhere, name)


def report_unresolved(root, name, requested):
    """Explain what to do when resolve() could not pick a wiki."""
    if root is None:
        sys.stderr.write('no wiki found here or in any parent directory.\n'
                         'run wiki_init.py to create one, or pass its path.\n')
        return 2
    available = wiki_paths.domains(root)
    if requested and name == requested:
        sys.stderr.write('no domain %r in %s\n' % (requested, root))
    else:
        sys.stderr.write('this wiki has several domains; pick one.\n')
    sys.stderr.write('domains: %s\n' % (', '.join(available) or '(none yet)'))
    sys.stderr.write('use --domain NAME, --all, or cd into the domain.\n')
    return 2


def compile_all(root):
    """Compile every domain. Reports each, returns nonzero if any had problems."""
    names = wiki_paths.domains(root)
    if not names:
        sys.stderr.write('no domains under %s\n' % root)
        return 2

    # Slugs owned by other domains, so a cross-domain [[link]] is not reported
    # as an unwritten page. Cross-domain links are allowed by design.
    elsewhere = {}
    for name in names:
        wiki_dir, _raw = wiki_paths.domain_paths(root, name)
        for p in wiki_paths.page_files(wiki_dir):
            elsewhere[slug_of(p)] = name

    worst = 0
    for i, name in enumerate(names):
        if i:
            print()
        print('domain: %s' % name)
        wiki_dir, _raw = wiki_paths.domain_paths(root, name)
        worst = max(worst, compile_one(wiki_dir, root, elsewhere, name))
    return worst


def compile_one(wiki_dir, root, elsewhere=None, domain=None):
    nodes, edges, problems = build(wiki_dir, root)
    if not nodes:
        sys.stderr.write('no pages found in %s (looked in %s/)\n'
                         % (wiki_paths.rel(wiki_dir, root),
                            '/, '.join(wiki_paths.PAGE_TYPES)))
        return 1

    out_dir = os.path.join(wiki_dir, 'graph')
    sharded = len(nodes) > SHARD_THRESHOLD
    try:
        # Everything here is regenerable, so clear it wholesale. Cleaning only
        # the files the current mode writes leaves phantoms behind when a tag
        # disappears or the wiki crosses the threshold in either direction.
        clear_output(out_dir)
        written = (emit_sharded(out_dir, nodes, edges) if sharded
                   else emit_single(out_dir, nodes, edges))
    except OSError as exc:
        sys.stderr.write('cannot write %s: %s\n' % (out_dir, exc))
        return 2

    typed = sum(1 for e in edges
                if e['relation'] not in ('mentions', 'sourced_from'))
    print('pages: %d  edges: %d (typed: %d)  %s'
          % (len(nodes), len(edges), typed,
             'sharded' if sharded else 'single file'))
    for path, size in written:
        print('  %s  %s' % (wiki_paths.rel(path, root), fmt(size)))

    # A dangling [[wikilink]] is a note about what to write next. A typed
    # relation pointing nowhere is different: it is a sourced factual claim
    # about a page that does not exist, so it counts as a problem.
    outside = elsewhere or {}
    missing = sorted({e['target'] for e in edges
                      if e['relation'] == 'mentions'
                      and e['target'] not in nodes})
    crossing = [d for d in missing
                if outside.get(d) and outside[d] != domain]
    dangling = [d for d in missing if d not in crossing]

    if crossing:
        print('\ncross-domain links: %d' % len(crossing))
        for d in crossing[:10]:
            print('  [[%s]] -> %s' % (d, outside[d]))
        if len(crossing) > 10:
            print('  ... and %d more' % (len(crossing) - 10))
    if dangling:
        print('\ndangling links (pages not written yet): %d' % len(dangling))
        for d in dangling[:10]:
            print('  [[%s]]' % d)
        if len(dangling) > 10:
            print('  ... and %d more' % (len(dangling) - 10))

    for e in edges:
        if e['relation'] in ('mentions', 'sourced_from'):
            continue
        if e['target'] in nodes or is_raw(e['target']):
            continue
        if outside.get(e['target']):
            continue  # lives in another domain, which is allowed
        problems.append('relation %s %s -> %s: no such page'
                        % (e['source'], e['relation'], e['target']))

    if problems:
        print('\nproblems: %d' % len(problems))
        for p in problems[:20]:
            print('  %s' % p)
        if len(problems) > 20:
            print('  ... and %d more' % (len(problems) - 20))
        return 1
    return 0


def fmt(n):
    return '%.1f KB' % (n / 1024.0) if n >= 1024 else '%d B' % n


if __name__ == '__main__':
    # Windows consoles default to cp949/cp1252 and choke on non-ASCII output.
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    sys.exit(main(sys.argv))
