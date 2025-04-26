"""Unit tests for chronograph visualization module."""

import unittest
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.axes import Axes
from daolite.utils.chronograph import (
    generate_chrono_plot,
    generate_chrono_plot_packetize,
    _plot_data_set,
    _plot_data_set_packetize,
)


class TestChronograph(unittest.TestCase):
    """Test chronograph visualization functionality."""

    def setUp(self):
        """Set up test fixtures."""
        # Create sample timing data
        self.n_samples = 50
        self.n_stages = 4
        self.timing_data = []

        # Generate sample timing data for multiple pipeline stages
        base_time = 0
        for stage in range(self.n_stages):
            times = np.zeros((self.n_samples, 2))
            for i in range(self.n_samples):
                times[i, 0] = base_time + i * 10
                times[i, 1] = times[i, 0] + 5 + stage * 2
            self.timing_data.append((times, f"Stage {stage}"))
            base_time += 5

    def test_plot_data_set(self):
        """Test single dataset plotting."""
        fig, ax = plt.subplots()
        plot_height = 0

        # Plot single dataset
        fig = _plot_data_set(
            self.timing_data[0][0][0],  # First sample of first stage
            fig,
            plot_height,
            "blue",
        )

        self.assertIsInstance(fig, Figure)
        self.assertTrue(len(ax.patches) > 0)  # Should have created rectangle
        plt.close(fig)

    def test_plot_data_set_packetize(self):
        """Test packetized dataset plotting."""
        fig, ax = plt.subplots()
        plot_height = 0

        # Plot packetized data
        fig = _plot_data_set_packetize(
            self.timing_data[0][0],  # All samples of first stage
            fig,
            plot_height,
            "blue",
        )

        self.assertIsInstance(fig, Figure)
        self.assertEqual(len(ax.patches), self.n_samples)  # One rect per sample
        plt.close(fig)

    def test_generate_chrono_plot(self):
        """Test chronological plot generation."""
        # Use a single interval per dataset (1D array)
        data_list = [(np.array([0, 5]), "Stage 1"), (np.array([10, 15]), "Stage 2")]
        fig, latency = generate_chrono_plot(
            data_list=data_list, title="Test Plot", xlabel="Time (μs)"
        )
        self.assertIsNotNone(fig)
        self.assertGreaterEqual(latency, 0)

        # Verify plot components
        ax = fig.gca()
        self.assertEqual(len(ax.get_yticklabels()), len(data_list))
        self.assertEqual(ax.get_title(), "Test Plot")
        self.assertEqual(ax.get_xlabel(), "Time (μs)")

        plt.close(fig)

    def test_generate_chrono_plot_packetize(self):
        """Test packetized chronological plot generation."""
        # Generate packetized plot
        fig, ax, latency = generate_chrono_plot_packetize(
            data_list=self.timing_data, title="Test Packetized Plot", xlabel="Time (μs)"
        )

        self.assertIsInstance(fig, Figure)
        self.assertIsInstance(ax, Axes)
        self.assertGreater(latency, 0)

        # Verify plot components
        self.assertEqual(len(ax.get_yticklabels()), self.n_stages)
        self.assertEqual(ax.get_title(), "Test Packetized Plot")
        self.assertEqual(ax.get_xlabel(), "Time (μs)")

        # Test with multiplot option
        fig, ax, latency = generate_chrono_plot_packetize(
            data_list=self.timing_data,
            title="Test Multiplot",
            xlabel="Time (μs)",
            multiplot=True,
        )

        self.assertIsInstance(fig, Figure)
        self.assertIsInstance(ax, Axes)
        self.assertGreater(latency, 0)

        # Multiplot should show more samples
        n_patches_normal = len(ax.patches)
        plt.close(fig)

        fig, ax, _ = generate_chrono_plot_packetize(
            data_list=self.timing_data, multiplot=False
        )
        self.assertGreater(n_patches_normal, len(ax.patches))

        plt.close("all")


if __name__ == "__main__":
    unittest.main()
