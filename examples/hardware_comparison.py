#!/usr/bin/env python
"""
Example script demonstrating how to use custom hardware configurations with DaoLite.

This script loads custom hardware configurations from YAML files and compares
their performance characteristics for typical adaptive optics workloads.
"""

import sys
import os
import matplotlib.pyplot as plt
import numpy as np


from daolite.compute import create_compute_resources_from_yaml
from daolite.compute import hardware

# Load custom resources from YAML files
custom_cpu = create_compute_resources_from_yaml("examples/custom_cpu.yaml")
custom_gpu = create_compute_resources_from_yaml("examples/custom_gpu.yaml")

# Define a range of workloads (memory sizes in bytes)
memory_sizes = np.logspace(6, 10, 5)  # From 1MB to 10GB
flops_sizes = np.logspace(9, 12, 5)  # From 1GFLOP to 1TFLOP

print("Comparing hardware performance for various workloads:")
print("=" * 80)
print(
    f"{'Memory Size (MB)':<15} {'FLOPs':<15} {'EPYC 9654 (μs)':<20} {'A100 80GB (μs)':<20} {'Custom CPU (μs)':<20} {'Custom GPU (μs)':<20}"
)
print("-" * 80)

# Create data structures for plotting
labels = ["EPYC 9654", "A100 80GB", "Custom CPU", "Custom GPU"]
cpu_times = []
gpu_times = []
custom_cpu_times = []
custom_gpu_times = []

# Calculate latencies for each workload
for memory_size, flops in zip(memory_sizes, flops_sizes):
    epyc_time = hardware.amd_epyc_9654().total_time(memory_size, flops)
    a100_time = hardware.nvidia_a100_80gb().total_time(memory_size, flops)
    custom_cpu_time = custom_cpu.total_time(memory_size, flops)
    custom_gpu_time = custom_gpu.total_time(memory_size, flops)

    # Store for plotting
    cpu_times.append(epyc_time)
    gpu_times.append(a100_time)
    custom_cpu_times.append(custom_cpu_time)
    custom_gpu_times.append(custom_gpu_time)

    # Print comparison
    print(
        f"{memory_size/1e6:<15.2f} {flops:<15.2e} {epyc_time:<20.2f} {a100_time:<20.2f} {custom_cpu_time:<20.2f} {custom_gpu_time:<20.2f}"
    )

# Plot the results
plt.figure(figsize=(12, 8))
x = np.arange(len(memory_sizes))
bar_width = 0.2
opacity = 0.8

plt.bar(
    x - 1.5 * bar_width,
    cpu_times,
    bar_width,
    alpha=opacity,
    color="blue",
    label=labels[0],
)
plt.bar(
    x - 0.5 * bar_width,
    gpu_times,
    bar_width,
    alpha=opacity,
    color="green",
    label=labels[1],
)
plt.bar(
    x + 0.5 * bar_width,
    custom_cpu_times,
    bar_width,
    alpha=opacity,
    color="red",
    label=labels[2],
)
plt.bar(
    x + 1.5 * bar_width,
    custom_gpu_times,
    bar_width,
    alpha=opacity,
    color="purple",
    label=labels[3],
)

plt.xlabel("Workload Size")
plt.ylabel("Latency (μs)")
plt.title("Latency Comparison Across Hardware Resources")
plt.xticks(x, [f"{m/1e6:.1f}MB" for m in memory_sizes])
plt.legend()
plt.yscale("log")
plt.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig("hardware_comparison.png")
print("\nPlot saved as 'hardware_comparison.png'")
print(
    "\nNote: This is a simplified model. Real-world performance may vary based on specific workloads."
)
