"""Reviewed A-share universe scope for AI-server and semiconductor themes.

Company names are intentionally not authoritative here. Runtime universe
construction must stamp names from Tushare/AkShare provider security lists.
"""

from .chokepoint_map import universe_codes


DEFAULT_A_SHARE_ALLOWLIST = universe_codes()
