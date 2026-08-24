"""Locate the wiki. Shared by wiki_init.py, wiki_graph.py, wiki_query.py.

Two layouts, both marked by a `.xllmwiki` file at the project root:

  single                          multi-domain
  ------                          ------------
  .xllmwiki                       .xllmwiki   {"root": "_WIKI"}
  wiki/{concept,entity,...}/      _WIKI/infra/{wiki,raw}/
  raw/                            _WIKI/poker/{wiki,raw}/

The marker is what lets the scripts run from any subdirectory. Without it they
would only work from the exact directory holding `wiki/`.

Standard library only.
"""
import io
import json
import os

MARKER = '.xllmwiki'
DEFAULTS = {'wiki': 'wiki', 'raw': 'raw', 'root': None}

# Pages live in one directory per type. The split is for humans: an Obsidian
# vault sidebar with 400 files in one folder is unusable, while four collapsible
# folders are navigable. `type:` in frontmatter stays authoritative -- the
# directory is a mirror of it, and lint reports any disagreement.
PAGE_TYPES = ('concept', 'entity', 'source', 'synthesis')


def find_root(start=None):
    """Walk up from `start` to the nearest marker. Returns a path or None."""
    cur = os.path.abspath(start or os.getcwd())
    seen = None
    while cur != seen:
        if os.path.isfile(os.path.join(cur, MARKER)):
            return cur
        seen, cur = cur, os.path.dirname(cur)

    # No marker: accept an unmarked single-domain tree so a wiki created by
    # hand keeps working before it has been initialised.
    cur = os.path.abspath(start or os.getcwd())
    seen = None
    while cur != seen:
        if looks_like_wiki(os.path.join(cur, 'wiki')):
            return cur
        seen, cur = cur, os.path.dirname(cur)
    return None


def looks_like_wiki(path):
    """True when `path` holds a page directory (a type dir, or legacy topics/)."""
    if not os.path.isdir(path):
        return False
    for sub in PAGE_TYPES + ('topics',):
        if os.path.isdir(os.path.join(path, sub)):
            return True
    return False


def read_config(root):
    """Read the marker. It may be empty, a human note, or JSON.

    Keys: `wiki` and `raw` name the directories; `root` names the container
    holding one subdirectory per domain (multi-domain layout).
    """
    cfg = dict(DEFAULTS)
    path = os.path.join(root, MARKER)
    try:
        text = io.open(path, encoding='utf-8').read().strip()
    except OSError:
        return cfg
    if not text:
        return cfg
    try:
        loaded = json.loads(text)
    except ValueError:
        # A marker with a human-written note in it is still a valid marker.
        return cfg
    if isinstance(loaded, dict):
        for k in DEFAULTS:
            v = loaded.get(k)
            if isinstance(v, str) and v:
                cfg[k] = v
    return cfg


def domains(root, cfg=None):
    """List domain names under the container, or [] for a single-domain wiki.

    A directory counts as a domain when it holds the wiki subdirectory named
    in the config, so unrelated folders in the container are ignored.
    """
    cfg = cfg or read_config(root)
    if not cfg['root']:
        return []
    base = os.path.join(root, cfg['root'])
    if not os.path.isdir(base):
        return []
    found = []
    for name in sorted(os.listdir(base)):
        if name.startswith('.'):
            continue
        if os.path.isdir(os.path.join(base, name, cfg['wiki'])):
            found.append(name)
    return found


def domain_paths(root, name, cfg=None):
    """(wiki_dir, raw_dir) for one domain."""
    cfg = cfg or read_config(root)
    base = os.path.join(root, cfg['root'], name)
    return os.path.join(base, cfg['wiki']), os.path.join(base, cfg['raw'])


def _domain_from_cwd(root, cfg, start=None):
    """Which domain is `start` inside, if any? Lets the scripts default to the
    domain the user is standing in rather than demanding --domain every time."""
    cur = os.path.abspath(start or os.getcwd())
    base = os.path.abspath(os.path.join(root, cfg['root']))
    if not (cur == base or cur.startswith(base + os.sep)):
        return None
    tail = os.path.relpath(cur, base)
    if tail in ('.', os.curdir):
        return None
    first = tail.split(os.sep)[0]
    return first if first in domains(root, cfg) else None


def resolve(arg=None, domain=None, start=None):
    """Return (wiki_dir, raw_dir, root, domain).

    `arg` is an explicit path: either a wiki directory or a project root, and
    it always wins over discovery. `domain` selects one domain in a
    multi-domain wiki; without it the domain containing the current directory
    is used, and a multi-domain wiki with no such context returns
    domain=None so the caller can ask which one.
    """
    if arg:
        arg = os.path.abspath(arg)
        if looks_like_wiki(arg):
            # Pointed straight at a wiki directory.
            parent = os.path.dirname(arg)
            cfg = read_config(find_root(parent) or parent)
            return arg, os.path.join(parent, cfg['raw']), parent, None
        root = arg
    else:
        root = find_root(start)
        if root is None:
            return None, None, None, None

    cfg = read_config(root)

    if not cfg['root']:
        return (os.path.join(root, cfg['wiki']),
                os.path.join(root, cfg['raw']), root, None)

    available = domains(root, cfg)
    name = domain or _domain_from_cwd(root, cfg, start)
    if name is None:
        # Caller must choose; expose the root so it can list them.
        return None, None, root, None
    if name not in available:
        return None, None, root, name  # caller reports the bad name
    w, r = domain_paths(root, name, cfg)
    return w, r, root, name


def page_files(wiki_dir):
    """Every page in the wiki, across the type directories.

    Also picks up a flat `topics/` layout so a wiki written before the split
    still compiles, and catches pages sitting loose in the wiki root.
    """
    seen, out = set(), []
    for sub in PAGE_TYPES + ('topics',):
        d = os.path.join(wiki_dir, sub)
        if not os.path.isdir(d):
            continue
        for name in sorted(os.listdir(d)):
            if not name.endswith('.md') or name.startswith('.'):
                continue
            p = os.path.join(d, name)
            if os.path.isfile(p):
                seen.add(name)
                out.append(p)
    return out


def find_page(wiki_dir, slug):
    """Locate one page by slug. Returns a path or None.

    This is why the type split costs nothing at the link layer: [[slug]]
    resolution happens here, once, instead of at every call site.
    """
    for sub in PAGE_TYPES + ('topics',):
        p = os.path.join(wiki_dir, sub, slug + '.md')
        if os.path.isfile(p):
            return p
    return None


def duplicate_slugs(wiki_dir):
    """Slugs that exist in more than one type directory.

    The failure mode of a type split: a page whose type changed and was copied
    rather than moved. Two files, one addressable name, and links silently
    resolve to whichever the scan hit first.
    """
    where = {}
    for p in page_files(wiki_dir):
        slug = os.path.splitext(os.path.basename(p))[0]
        where.setdefault(slug, []).append(p)
    return {s: ps for s, ps in where.items() if len(ps) > 1}


def type_dir(wiki_dir, page_type):
    """Where a page of this type belongs."""
    name = page_type if page_type in PAGE_TYPES else 'concept'
    return os.path.join(wiki_dir, name)


def rel(path, root):
    """Path relative to the project root, with forward slashes."""
    try:
        return os.path.relpath(path, root).replace(os.sep, '/')
    except ValueError:
        # Different drive on Windows; an absolute path is the honest answer.
        return path.replace(os.sep, '/')
