import unittest
import numpy as np
import matplotlib

matplotlib.use("Agg")  # Use non-interactive backend for tests
from daolite.utils import chronograph


class TestChronographUtils(unittest.TestCase):
    def setUp(self):
        # Create simple timing data
        self.data1 = np.array([0, 10])
        self.data2 = np.array([5, 20])
        self.packet_data = np.array([[0, 10], [10, 20], [20, 30]])
        self.data_list = [(self.data1, "Stage 1"), (self.data2, "Stage 2")]
        self.packet_data_list = [
            (self.packet_data, "Packet Stage 1"),
            (self.packet_data + 10, "Packet Stage 2"),
        ]

    def test_plot_data_set(self):
        from matplotlib.figure import Figure

        fig = matplotlib.pyplot.figure()
        fig2 = chronograph._plot_data_set(self.data1, fig, 0, "blue")
        self.assertIsInstance(fig2, Figure)

    def test_plot_data_set_packetize(self):
        from matplotlib.figure import Figure

        fig = matplotlib.pyplot.figure()
        fig2 = chronograph._plot_data_set_packetize(self.packet_data, fig, 0, "green")
        self.assertIsInstance(fig2, Figure)

    def test_generate_chrono_plot(self):
        fig, latency = chronograph.generate_chrono_plot(
            self.data_list, title="Test", xlabel="Time"
        )
        self.assertIsNotNone(fig)
        self.assertGreaterEqual(latency, 0)

    def test_generate_chrono_plot_packetize(self):
        fig, ax, latency = chronograph.generate_chrono_plot_packetize(
            self.packet_data_list, title="Test Packet", xlabel="Time"
        )
        self.assertIsNotNone(fig)
        self.assertIsNotNone(ax)
        self.assertGreaterEqual(latency, 0)

    def test_generate_chrono_plot_packetize_multiplot(self):
        fig, ax, latency = chronograph.generate_chrono_plot_packetize(
            self.packet_data_list, multiplot=True
        )
        self.assertIsNotNone(fig)
        self.assertIsNotNone(ax)
        self.assertGreaterEqual(latency, 0)

    def test_empty_data(self):
        # Should handle empty data gracefully
        with self.assertRaises(Exception):
            chronograph.generate_chrono_plot([], title="Empty", xlabel="Time")


if __name__ == "__main__":
    unittest.main()
