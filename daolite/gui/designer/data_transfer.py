"""
Data transfer utilities for the pipeline designer.

This module provides functions for estimating data transfer sizes and
determining appropriate transfer methods between components.
"""

import logging
from daolite.common import ComponentType

# Set up logging
logger = logging.getLogger('DataTransfer')

def determine_transfer_chain(src_comp, dest_comp):
    """
    Determine the transfer chain (list of transfer types) between two components.
    Handles multi-step transfers such as GPU->GPU across computers.
    Returns a list of transfer types in order (e.g., ["PCIe", "Network", "PCIe"])
    """
    from .component_container import GPUBox, ComputeBox
    chain = []
    src_res = src_comp.get_compute_resource()
    dest_res = dest_comp.get_compute_resource()
    src_parent = src_comp.parentItem()
    dest_parent = dest_comp.parentItem()

    # Camera components always connect via network (and PCIe if dest is GPU)
    if src_comp.component_type == ComponentType.CAMERA:
        chain.append("Network")
        if dest_parent and isinstance(dest_parent, GPUBox):
            chain.append("PCIe")
        return chain

    # Helper to get ComputeBox for a component
    def get_compute_box(comp):
        parent = comp.parentItem() if hasattr(comp, 'parentItem') else None
        if parent and isinstance(parent, ComputeBox):
            return parent
        if parent and isinstance(parent, GPUBox):
            grandparent = parent.parentItem() if hasattr(parent, 'parentItem') else None
            if grandparent and isinstance(grandparent, ComputeBox):
                return grandparent
        return None

    src_is_gpu = src_parent and isinstance(src_parent, GPUBox)
    dest_is_gpu = dest_parent and isinstance(dest_parent, GPUBox)
    src_box = get_compute_box(src_comp)
    dest_box = get_compute_box(dest_comp)
    different_computers = src_box and dest_box and src_box != dest_box

    # GPU -> GPU (different computers): PCIe (GPU1->host1) + Network (host1->host2) + PCIe (host2->GPU2)
    if src_is_gpu and dest_is_gpu and different_computers:
        chain.extend(["PCIe", "Network", "PCIe"])
        return chain
    # GPU -> CPU (different computers): PCIe (GPU->host1) + Network (host1->host2)
    if src_is_gpu and not dest_is_gpu and different_computers:
        chain.extend(["PCIe", "Network"])
        return chain
    # CPU -> GPU (different computers): Network (host1->host2) + PCIe (host2->GPU)
    if not src_is_gpu and dest_is_gpu and different_computers:
        chain.extend(["Network", "PCIe"])
        return chain
    # CPU -> CPU (different computers): Network
    if not src_is_gpu and not dest_is_gpu and different_computers:
        chain.append("Network")
        return chain
    # CPU <-> GPU (same computer): PCIe
    if src_is_gpu != dest_is_gpu and not different_computers:
        chain.append("PCIe")
        return chain
    # Fallback to single transfer type if any
    ttype = determine_transfer_type(src_comp, dest_comp)
    if ttype:
        chain.append(ttype)
    return chain

def determine_transfer_type(src_comp, dest_comp):
    """
    Backward-compatible: returns the first transfer type in the chain, or None.
    """
    chain = determine_transfer_chain(src_comp, dest_comp)
    return chain[0] if chain else None

def estimate_data_size(src_comp, dest_comp):
    """
    Estimate data size transferred between components in bits.
    
    Args:
        src_comp: Source component
        dest_comp: Destination component
        
    Returns:
        int: Estimated data size in bits
    """
    # Only operate on objects with component_type
    if not hasattr(src_comp, 'component_type') or not hasattr(dest_comp, 'component_type'):
        return 0

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