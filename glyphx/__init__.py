__version__ = "v1.2.9"

from .figure import Figure
from .layout import Axes, grid
from .themes import themes
from .utils import normalize

# Core plotting interface
from .plot import plot

# Base chart types
from .series import (
    LineSeries,
    BarSeries,
    ScatterSeries,
    PieSeries,
    DonutSeries,
    HistogramSeries,
    HeatmapSeries,
    BoxPlotSeries
)

# Advanced chart types
from .grouped_bar import GroupedBarSeries
from .violin_plot import ViolinPlotSeries
from .swarm_plot import SwarmPlotSeries
from .count_plot import CountPlotSeries

# Seaborn-style composite plots
from .facet_plot import facet_plot
from .pairplot import pairplot
from .jointplot import jointplot
from .lmplot import lmplot

__all__ = [
    "Figure",
    "Axes",
    "grid",
    "themes",
    "normalize",
    "plot",
    "LineSeries",
    "BarSeries",
    "ScatterSeries",
    "PieSeries",
    "DonutSeries",
    "HistogramSeries",
    "HeatmapSeries",
    "BoxPlotSeries",
    "GroupedBarSeries",
    "ViolinPlotSeries",
    "SwarmPlotSeries",
    "CountPlotSeries",
    "facet_plot",
    "pairplot",
    "jointplot",
    "lmplot"
]
