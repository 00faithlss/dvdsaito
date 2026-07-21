"""
Motor de procesamiento de imagen de DVD Saito.

Desde afuera se usa asi:

    from saito import engine as eng
    eng.process(imagen, ajustes)
    eng.FILTERS, eng.FILTER_CATEGORIES, eng.DEFAULTS, eng.ASPECTS

El resto de los modulos (helpers, filters, effects, adjustments, pipeline)
son las partes internas.
"""

from .pipeline import DEFAULTS, ASPECTS, process, output_size
from .filters import FILTERS, FILTER_CATEGORIES

__all__ = ["DEFAULTS", "ASPECTS", "process", "output_size",
           "FILTERS", "FILTER_CATEGORIES"]
