"""
Data transfer utilities for the pipeline designer.

This module provides functions for estimating data transfer sizes and
determining appropriate transfer methods between components.
"""

import logging
from daolite.common import ComponentType

# Set up logging
logger = logging.getLogger('DataTransfer')

def determine_transfer_type(src_comp, dest_comp):
    """
    Determine the type of transfer between two components.
    
    Args:
        src_comp: Source component
        dest_comp: Destination component
        
    Returns:
        str: Transfer type ('Network' or 'PCIe') or None if no transfer needed
    """
    # Get compute resources and parent containers
    src_res = src_comp.get_compute_resource()
    dest_res = dest_comp.get_compute_resource()
    src_parent = src_comp.parentItem()
    dest_parent = dest_comp.parentItem()
    
    # Camera components always connect via network
    if src_comp.component_type == ComponentType.CAMERA:
        return "Network"
    
    # Check if components are in different compute boxes
    if (src_parent and dest_parent and 
        src_parent != dest_parent and
        isinstance(src_parent, 'ComputeBox') and 
        isinstance(dest_parent, 'ComputeBox')):
        return "Network"
    
    # Check for CPU-GPU transfers
    from .components import GPUBox
    if ((isinstance(src_parent, GPUBox) and not isinstance(dest_parent, GPUBox)) or
        (not isinstance(src_parent, GPUBox) and isinstance(dest_parent, GPUBox))):
        return "PCIe"
    
    # Check based on hardware type
    if src_res and dest_res:
        src_hw = getattr(src_res, 'hardware', 'CPU')
        dest_hw = getattr(dest_res, 'hardware', 'CPU')
        if src_hw != dest_hw:
            if 'GPU' in (src_hw, dest_hw):
                return "PCIe"
            else:
                return "Network"
    
    # No transfer needed or couldn't determine
    return None

def estimate_data_size(src_comp, dest_comp):
    """
    Estimate data size transferred between components in bits.
    
    Args:
        src_comp: Source component
        dest_comp: Destination component
        
    Returns:
        int: Estimated data size in bits
    """
    # Default values for common AO data sizes
    if src_comp.component_type == ComponentType.CAMERA:
        # Camera output is typically pixel data
        n_pixels = src_comp.params.get("n_pixels", 1024 * 1024)  # Default 1MP
        bit_depth = src_comp.params.get("bit_depth", 16)  # Default 16-bit
        return n_pixels * bit_depth

    elif src_comp.component_type == ComponentType.CALIBRATION:
        # Calibration typically outputs calibrated pixel data
        n_pixels = src_comp.params.get("n_pixels", 1024 * 1024)
        bit_depth = src_comp.params.get("output_bit_depth", 16)
        return n_pixels * bit_depth
        
    elif src_comp.component_type == ComponentType.CENTROIDER:
        # Centroider outputs slope measurements
        n_subaps = src_comp.params.get("n_valid_subaps", 6400)  # Default 80×80
        bit_size = 32  # Usually float32
        return n_subaps * 2 * bit_size  # X and Y slopes
        
    elif src_comp.component_type == ComponentType.RECONSTRUCTION:
        # Reconstruction outputs actuator commands
        n_actuators = src_comp.params.get("n_acts", 5000)  # Default ELT scale
        bit_size = 32  # Usually float32
        return n_actuators * bit_size
        
    elif src_comp.component_type == ComponentType.CONTROL:
        # Control outputs actuator commands (possibly with telemetry)
        n_actuators = src_comp.params.get("n_acts", 5000)
        bit_size = 32
        return n_actuators * bit_size
    
    # Fallback to a reasonable default for AO data
    return 1024 * 1024 * 16  # 1MP at 16-bit