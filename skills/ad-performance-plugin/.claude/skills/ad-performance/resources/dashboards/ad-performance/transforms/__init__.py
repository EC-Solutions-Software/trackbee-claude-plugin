"""Package marker — lets sibling modules use relative imports.

The orchestrator loads each module as a child of this package so that
`from . import _fmt as f` resolves correctly without putting the parent
on sys.path.
"""
