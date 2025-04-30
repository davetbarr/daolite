"""
Example showing how to use separate camera readout and network components.

This example demonstrates how to model camera readout and network transfer as separate
components in a pipeline, which more accurately reflects real-world behavior.
"""

import numpy as np
from daolite.compute import ComputeResources
from daolite.simulation.camera import PCOCamLink, GigeVisionCamera, RollingShutterCamera
from daolite.utils.network import CameraDataTransfer


def main():
    # Initialize compute resources
    compute_res = ComputeResources()
    compute_res.set_network_bandwidth(10.0)  # 10 Gbps network
    
    # Camera parameters
    n_pixels = 1024 * 1024  # 1 megapixel camera
    bits_per_pixel = 16  # 16-bit pixels
    n_groups = 50  # Number of readout groups
    
    print("Comparing different camera types with separate network transfer:")
    print("="*80)
    
    # PCO CameraLink
    print("\nPCO CameraLink Camera:")
    # Get pixel availability timing (when pixels are ready from camera)
    pco_pixel_timings = PCOCamLink(compute_res, n_pixels, group=n_groups, debug=True)
    # Calculate network transfer timing based on pixel availability
    pco_network_timings = CameraDataTransfer(
        compute_res, pco_pixel_timings, n_pixels, bits_per_pixel, debug=True
    )
    # Calculate end-to-end latency (from first pixel available to last pixel transferred)
    pco_latency = pco_network_timings[-1, 1] - pco_pixel_timings[0, 0]
    print(f"PCO CameraLink end-to-end latency: {pco_latency:.2f} μs")
    
    # GigE Vision Camera
    print("\nGigE Vision Camera:")
    # Get pixel availability timing (when pixels are ready from camera)
    gige_pixel_timings = GigeVisionCamera(compute_res, n_pixels, group=n_groups, debug=True)
    # Calculate network transfer timing based on pixel availability
    gige_network_timings = CameraDataTransfer(
        compute_res, gige_pixel_timings, n_pixels, bits_per_pixel, debug=True
    )
    # Calculate end-to-end latency (from first pixel available to last pixel transferred)
    gige_latency = gige_network_timings[-1, 1] - gige_pixel_timings[0, 0]
    print(f"GigE Vision end-to-end latency: {gige_latency:.2f} μs")
    
    # Rolling Shutter Camera
    print("\nRolling Shutter Camera:")
    # Get pixel availability timing (when pixels are ready from camera)
    rs_pixel_timings = RollingShutterCamera(compute_res, n_pixels, group=n_groups, debug=True)
    # Calculate network transfer timing based on pixel availability
    rs_network_timings = CameraDataTransfer(
        compute_res, rs_pixel_timings, n_pixels, bits_per_pixel, debug=True
    )
    # Calculate end-to-end latency (from first pixel available to last pixel transferred)
    rs_latency = rs_network_timings[-1, 1] - rs_pixel_timings[0, 0]
    print(f"Rolling Shutter end-to-end latency: {rs_latency:.2f} μs")
    
    # Compare results
    print("\nLatency Comparison:")
    print(f"PCO CameraLink: {pco_latency:.2f} μs")
    print(f"GigE Vision:    {gige_latency:.2f} μs")
    print(f"Rolling Shutter: {rs_latency:.2f} μs")


if __name__ == "__main__":
    main()