#!/usr/bin/env python3
"""Create a wiki, or add a domain to an existing multi-domain wiki.

Standard library only.

    python3 wiki_init.py                          # single wiki here
    python3 wiki_init.py --domain infra           # multi-domain, first domain
    python3 wiki_init.py --domain poker           # add another domain
    python3 wiki_init.py [root] [--container NAME]
                         [--wiki-dir NAME] [--raw-dir NAME] [--force]

Writes the tree, a .xllmwiki marker so the other scripts find the wiki from
any subdirectory, and starter index/log files. Never overwrites existing
content; --force only rewrites the marker.
"""
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wiki_paths  # noqa: E402

DEFAULT_CONTAINER = '_WIKI'

INDEX = """# Index

The map of this wiki -- every page, one line each. A page missing from here is
invisible, so add its line in the same pass that creates it.

- [[SCHEMA]] — 이 위키의 지역 규약: 태그 목록과 고유 규칙
- [[log]] — 무엇을 언제 흡수했는지의 기록
- [purpose.md](../purpose.md) — 이 위키가 무엇을 위한 것인가 (없으면 만든다)

## Pages

<!-- - [[slug]] -- one-line description -->
"""

LOG = """# Log

Append-only record of what was ingested when. This is the audit trail that
makes staleness diagnosable later.

<!-- - 2026-01-01 raw/source.md -> created: [[a]], [[b]] | extended: [[c]] -->
"""

GITIGNORE = """# Compiled graph index -- regenerable from the markdown at any time.
graph/
"""

CONTAINER_SCHEMA = """# Conventions (all domains)

Rules that apply across every domain here. A domain's own SCHEMA.md adds to
this; it does not replace it.

Paths live in `.xllmwiki`, not here.

## Shared tags

Tags meaningful in more than one domain. Domain-specific ones belong in that
domain's SCHEMA.md.

<!-- - benchmark -- carries measured numbers; always name the hardware -->

## Cross-domain rules

<!-- - A page belongs to the domain that owns the question, not the source. -->
"""

SCHEMA = """# Conventions

Local rules for this wiki. The skill supplies the defaults; this file records
what is specific to *this* body of knowledge. Keep it short -- every line here
is a line someone has to read before writing a page.

Paths and thresholds live in `.xllmwiki`, not here, so there is one place to
change them.

## Tags in use

Reuse before inventing. Add a line when you adopt a tag, delete it when the
last page drops it.

<!-- - inference -- runtime cost, latency, memory -->

## Local rules

<!-- - Korean pages keep Korean titles; do not translate slugs. -->
<!-- - Benchmark numbers always carry the hardware they were measured on. -->
"""


def write_if_absent(path, text, force=False):
    if os.path.exists(path) and not force:
        return False
    with io.open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(text)
    return True


def take_value(args, flag):
    """Pull `--flag value` out of args, returning the value or None."""
    if flag not in args:
        return None
    i = args.index(flag)
    if i + 1 >= len(args) or args[i + 1].startswith('--'):
        sys.stderr.write('%s needs a value\n' % flag)
        sys.exit(2)
    value = args[i + 1]
    del args[i:i + 2]
    return value


def check_name(flag, value):
    if os.sep in value or (os.altsep and os.altsep in value):
        sys.stderr.write('%s must be a single directory name, not a path: %s\n'
                         % (flag, value))
        sys.exit(2)


def seed_wiki(wiki_dir, raw_dir, root):
    """Create one wiki+raw pair with its starter files. Returns created paths."""
    # One directory per page type. The split is for humans -- an Obsidian
    # sidebar with hundreds of files in one folder is unusable.
    for t in wiki_paths.PAGE_TYPES:
        os.makedirs(os.path.join(wiki_dir, t), exist_ok=True)
    os.makedirs(raw_dir, exist_ok=True)
    created = []
    for name, text in (('index.md', INDEX), ('log.md', LOG),
                       ('SCHEMA.md', SCHEMA), ('.gitignore', GITIGNORE)):
        p = os.path.join(wiki_dir, name)
        if write_if_absent(p, text):
            created.append(wiki_paths.rel(p, root))
    return created


def seed_container(root, container, wiki_name):
    """Root-level index and SCHEMA for a multi-domain wiki.

    The root index lists domains, not pages -- that is what makes it useful
    without duplicating any domain's index. No root log.md: ingestion always
    happens inside a domain, so there is nothing for a root log to record.
    """
    base = os.path.join(root, container)
    os.makedirs(base, exist_ok=True)
    created = []
    names = wiki_paths.domains(root)
    lines = ['# Domains', '',
             'One line per domain. Each domain keeps its own index of pages.',
             '',
             '- [[SCHEMA]] — 모든 도메인에 적용되는 공통 규약',
             '',
             '## 도메인', '']
    for n in names:
        # A relative link, not a [[wikilink]]: the target is index.md in another
        # directory, and every domain has one by that name -- a bare [[index]]
        # would be ambiguous in Obsidian.
        lines.append('- **%s** — [%s/%s/index.md](%s/%s/index.md)'
                     % (n, n, wiki_name, n, wiki_name))
    if not names:
        lines.append('<!-- - **name** — what this domain covers -->')
    idx = os.path.join(base, 'index.md')
    # Rewritten every run: it is a generated list of domains, and a stale one
    # hides the domain someone just added.
    with io.open(idx, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
    created.append(wiki_paths.rel(idx, root))
    sp = os.path.join(base, 'SCHEMA.md')
    if write_if_absent(sp, CONTAINER_SCHEMA):
        created.append(wiki_paths.rel(sp, root))
    return created


def main(argv):
    args = argv[1:]
    force = '--force' in args
    args = [a for a in args if a != '--force']

    domain = take_value(args, '--domain')
    container = take_value(args, '--container')
    wiki_name = take_value(args, '--wiki-dir') or 'wiki'
    raw_name = take_value(args, '--raw-dir') or 'raw'
    for flag, value in (('--wiki-dir', wiki_name), ('--raw-dir', raw_name),
                        ('--domain', domain), ('--container', container)):
        if value:
            check_name(flag, value)
    if wiki_name == raw_name:
        sys.stderr.write('wiki and raw directories must differ\n')
        return 2

    root = os.path.abspath(args[0]) if args else os.getcwd()
    existing = wiki_paths.find_root(root)

    # Adding a domain to a wiki that already exists is the common second run,
    # so it is not treated as a conflict.
    if existing and domain:
        cfg = wiki_paths.read_config(existing)
        if not cfg['root']:
            sys.stderr.write(
                'the wiki at %s is single-domain (no container in %s).\n'
                'convert it by moving wiki/ and raw/ under a container '
                'directory and setting {"root": "..."} in the marker.\n'
                % (existing, wiki_paths.MARKER))
            return 2
        root, wiki_name, raw_name = existing, cfg['wiki'], cfg['raw']
        container = cfg['root']
    elif existing and not force:
        cfg = wiki_paths.read_config(existing)
        names = wiki_paths.domains(existing, cfg)
        print('a wiki already exists at %s' % existing)
        if cfg['root']:
            print('  layout: %s/<domain>/{%s,%s}'
                  % (cfg['root'], cfg['wiki'], cfg['raw']))
            print('  domains: %s' % (', '.join(names) or '(none yet)'))
            print('\nadd one with: wiki_init.py --domain <name>')
        else:
            print('  layout: %s/ and %s/' % (cfg['wiki'], cfg['raw']))
        print('nothing changed. pass --force to rewrite its marker.')
        return 0

    if container is None and domain:
        container = DEFAULT_CONTAINER

    try:
        if container:
            base = os.path.join(root, container, domain)
            wiki_dir = os.path.join(base, wiki_name)
            raw_dir = os.path.join(base, raw_name)
        else:
            wiki_dir = os.path.join(root, wiki_name)
            raw_dir = os.path.join(root, raw_name)

        created = seed_wiki(wiki_dir, raw_dir, root)

        marker = os.path.join(root, wiki_paths.MARKER)
        cfg = {}
        if container:
            cfg['root'] = container
        if wiki_name != 'wiki':
            cfg['wiki'] = wiki_name
        if raw_name != 'raw':
            cfg['raw'] = raw_name
        if cfg:
            body = json.dumps(cfg, ensure_ascii=False) + '\n'
        else:
            body = ('# xllmwiki root. Marks the wiki so the scripts find it\n'
                    '# from any subdirectory. Safe to keep in git.\n')
        write_if_absent(marker, body, force or bool(domain))

        # After the marker, so domains() can read the layout it declares.
        if container:
            created += seed_container(root, container, wiki_name)
    except OSError as exc:
        sys.stderr.write('cannot create the wiki: %s\n' % exc)
        return 2

    types = '{%s}' % ','.join(wiki_paths.PAGE_TYPES)
    print('wiki root: %s' % root)
    if container:
        print('  domain: %s' % domain)
        print('  %s/%s/%s/%s/' % (container, domain, wiki_name, types))
        print('  %s/%s/%s/' % (container, domain, raw_name))
    else:
        print('  %s/%s/   pages, one directory per type' % (wiki_name, types))
        print('  %s/          verbatim sources' % raw_name)
    print('  %s        marker' % wiki_paths.MARKER)
    for c in created:
        print('  %s' % c)
    if not created:
        print('  (starter files already existed)')

    if container:
        names = wiki_paths.domains(root)
        print('\ndomains: %s' % ', '.join(names))
    print('\npurpose.md is not created automatically -- write it with the '
          'skill so the goals are yours, not a template.')
    return 0


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    sys.exit(main(sys.argv))
