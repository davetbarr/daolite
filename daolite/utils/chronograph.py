"""
Chronograph module for visualizing timing data in adaptive optics systems.

This module provides tools for creating chronological visualizations of processing
pipeline timing data, including latency calculations and multi-stage timing plots.
"""

from typing import List, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np
from cycler import cycler
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle


def _plot_data_set(
    data_set: np.ndarray, figure: Figure, plot_height: float, color: str
) -> Figure:
    """Helper to plot a single timing dataset as a rectangle."""
    ax = figure.gca()
    # Ensure data_set is 1D and has two elements
    if hasattr(data_set, "__len__") and len(data_set) == 2:
        x = float(data_set[0])
        width = float(data_set[1] - data_set[0])
    else:
        raise ValueError(
            "data_set must be a 1D array or list with two elements [start, end]"
        )
    height = -1
    rect = Rectangle((x, plot_height), width, height, fill=True, color=color)
    ax.add_patch(rect)
    return figure


def _plot_data_set_packetize(
    data_set: np.ndarray, figure: Figure, plot_height: float, color: str
) -> Figure:
    """Helper to plot packetized timing data as rectangles."""
    ax = figure.gca()
    for i in range(len(data_set)):
        width = data_set[i, 1] - data_set[i, 0]
        x = data_set[i, 0]
        rect = Rectangle(
            (x, plot_height), width, -1, fill=True, facecolor=color, edgecolor="black"
        )
        ax.add_patch(rect)
    return figure


def generate_chrono_plot(
    data_list: List[Tuple[np.ndarray, str]], title: str = "", xlabel: str = ""
) -> Tuple[Figure, float]:
    """
    Generate a chronological plot for timing data.

    Args:
        data_list: List of tuples containing (timing_data, label)
                  timing_data is a numpy array with start/end times
        title: Plot title
        xlabel: X-axis label

    Returns:
        tuple: (matplotlib figure, latency in microseconds)
    """
    plots = len(data_list)
    colors = plt.cm.viridis(np.linspace(0, 1, plots))
    color_cycle = cycler("color", colors)
    plot_colors = [c["color"] for c in color_cycle]

    if not data_list:
        raise ValueError("data_list cannot be empty")

    fig, ax = plt.subplots()
    plot_height = 0

    # Plot each dataset
    for timing_data, _ in data_list:
        fig = _plot_data_set(timing_data, fig, plot_height, plot_colors[-plot_height])
        plot_height -= 1

    # Configure plot limits and labels
    max_x = np.max(data_list[-1][0][1]) + 100
    plt.xlim(0, max_x)
    plt.ylim(plot_height - 1, 0)
    plt.title(title)
    plt.xlabel(xlabel)

    # Set y-axis labels
    labels = [label for _, label in data_list]
    heights = [i - 0.5 for i in range(len(labels))]
    ax.set_yticks(heights, labels=labels)

    # Calculate and display latency
    end_of_readout = data_list[0][0][1]
    end_of_rtc = data_list[-1][0][1]
    latency = end_of_rtc - end_of_readout

    # Draw latency indicators
    ax.hlines(plot_height - 1, end_of_readout, end_of_rtc, color="black")
    ax.vlines(end_of_readout, plot_height - 1, 0, color="black", linestyles="dashed")
    ax.vlines(
        end_of_rtc, plot_height - 1, plot_height, color="black", linestyles="dashed"
    )
    ax.text(end_of_readout + 5, plot_height - 0.9, f"latency - {int(latency)} μs")

    # Adjust figure size
    width = fig.get_figwidth()
    height = fig.get_figheight()
    fig.set_figwidth(width * 1.5)
    fig.set_figheight(height)

    return fig, latency


def generate_chrono_plot_packetize(
    data_list: List[Tuple[np.ndarray, str]],
    title: str = "",
    xlabel: str = "",
    multiplot: bool = False,
    latency_start_idx: Optional[int] = None,
    latency_end_idx: Optional[int] = None,
) -> Tuple[Figure, Axes, float]:
    """
    Generate a chronological plot for packetized timing data.

    Args:
        data_list: List of tuples containing (timing_data, label)
                  timing_data is a numpy array with start/end times
        title: Plot title
        xlabel: X-axis label
        multiplot: Whether to show multiple frames (past/future)
        latency_start_idx: Index of component to start latency measurement (None = first component)
        latency_end_idx: Index of component to end latency measurement (None = last component)

    Returns:
        tuple: (matplotlib figure, axes, latency in microseconds)
    """
    if multiplot:
        # Extend datasets one frame in past and future
        new_data_list = []
        for timing_data, label in data_list:
            shape = timing_data.shape
            new_data = np.zeros((shape[0] * 3, shape[1]))
            new_data[: shape[0], :] = timing_data - 500
            new_data[shape[0] : shape[0] * 2, :] = timing_data
            new_data[shape[0] * 2 :, :] = timing_data + 500
            new_data_list.append([new_data, label])
        orig_data_list = data_list
        data_list = new_data_list

    # Generate color scheme
    plots = len(data_list)
    colors = plt.cm.viridis(np.linspace(0, 1, plots))
    color_cycle = cycler("color", colors)
    plot_colors = [c["color"] for c in color_cycle]

    # Create plot
    fig, ax = plt.subplots()
    plot_height = 0

    # Plot each dataset
    for timing_data, _ in data_list:
        fig = _plot_data_set_packetize(
            timing_data, fig, plot_height, plot_colors[abs(plot_height)]
        )
        plot_height -= 1

    # Calculate plot limits
    max_x = 0
    if multiplot:
        for timing_data, _ in orig_data_list:
            max_x = max(max_x, np.max(timing_data) + 100)
    else:
        for timing_data, _ in data_list:
            max_x = max(max_x, np.max(timing_data) + 100)

    # Configure plot
    plt.xlim(0, max_x)
    plt.ylim(plot_height - 1, 0)
    plt.title(title)
    plt.xlabel(xlabel)

    # Set y-axis labels - Fix the label alignment issue by using the negative plot heights
    labels = [label for _, label in data_list]
    heights = [
        -i - 0.5 for i in range(len(labels))
    ]  # Changed to align with plot heights
    ax.set_yticks(heights, labels=labels)

    # Calculate and display latency using specified indices or defaults
    start_idx = latency_start_idx if latency_start_idx is not None else 0
    end_idx = latency_end_idx if latency_end_idx is not None else len(data_list) - 1

    end_of_readout = data_list[start_idx][0][-1, 1]
    end_of_rtc = data_list[end_idx][0][-1, 1]
    latency = end_of_rtc - end_of_readout

    # Draw latency indicators
    ax.hlines(plot_height - 1, end_of_readout, end_of_rtc, color="black")
    ax.vlines(end_of_readout, plot_height - 1, 0, color="black", linestyles="dashed")
    ax.vlines(
        end_of_rtc, plot_height - 1, plot_height, color="black", linestyles="dashed"
    )
    ax.text(end_of_readout + 5, plot_height - 0.9, f"latency - {int(latency)} μs")

    # Adjust figure size
    width = fig.get_figwidth()
    height = fig.get_figheight()
    fig.set_figwidth(width * 1.5)
    fig.set_figheight(height)

    return fig, ax, latency
