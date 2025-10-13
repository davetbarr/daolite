#!/usr/bin/env python
"""
Simple test script for compute resources.
"""

from daolite.compute import create_compute_resources_from_yaml
from daolite.compute.hardware import intel_xeon_8480, nvidia_h100_80gb

# Test built-in resources
gpu = nvidia_h100_80gb()
cpu = intel_xeon_8480()

# Test YAML resources
yaml_gpu = create_compute_resources_from_yaml("examples/custom_gpu.yaml")

# Compare performance for a simple computation
memory_size = 1e9  # 1 GB
flops = 1e12  # 1 TFLOP

print(f"H100 GPU latency: {gpu.total_time(memory_size, flops):.2f} μs")
print(f"Xeon CPU latency: {cpu.total_time(memory_size, flops):.2f} μs")
print(f"Custom GPU latency: {yaml_gpu.total_time(memory_size, flops):.2f} μs")

# Show memory bandwidth comparison
print("\nMemory Bandwidth:")
print(f"H100 GPU: {gpu.get_memory_bandwidth() / 1e9:.1f} GB/s")
print(f"Xeon CPU: {cpu.get_memory_bandwidth() / 1e9:.1f} GB/s")
print(f"Custom GPU: {yaml_gpu.get_memory_bandwidth() / 1e9:.1f} GB/s")
