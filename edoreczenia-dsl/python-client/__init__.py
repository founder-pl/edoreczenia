"""
e-Doręczenia DSL - Python Client

Klient DSL do obsługi API e-Doręczeń z logowaniem do Markdown.
"""

from .client import EDoreczeniaClient
from .logger import MarkdownLogger
from .scenarios import run_all_scenarios

__version__ = '1.0.0'
__all__ = ['EDoreczeniaClient', 'MarkdownLogger', 'run_all_scenarios']
