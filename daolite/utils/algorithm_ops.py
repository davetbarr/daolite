"""
Algorithm operation utilities for computing FLOPS and memory requirements.

This module provides utility functions to calculate the computational complexity
(FLOPS) and memory requirements for common algorithms used in adaptive optics
systems, such as FFT, matrix operations, sorting, correlation algorithms,
calibration, and control operations.
"""

import numpy as np


# FFT operation utilities
def _fft_flops(m: int, n: int) -> int:
    """
    Calculate number of FLOPS for FFT operation.
    
    Args:
        m: First dimension size
        n: Second dimension size
        
    Returns:
        int: Number of floating point operations
    """
    return 5 * m * n * np.log2(m)


def _fft_mem(m: int, n: int) -> int:
    """
    Calculate memory requirement for FFT operation.
    
    Args:
        m: First dimension size
        n: Second dimension size
        
    Returns:
        int: Memory requirement in elements
    """
    return 2 * m * n


# Complex conjugate operation utilities
def _conjugate_flops(m: int, n: int) -> int:
    """
    Calculate FLOPS for complex conjugate operation.
    
    Args:
        m: First dimension size
        n: Second dimension size
        
    Returns:
        int: Number of floating point operations
    """
    return m * n


def _conjugate_mem(m: int, n: int) -> int:
    """
    Calculate memory for complex conjugate operation.
    
    Args:
        m: First dimension size
        n: Second dimension size
        
    Returns:
        int: Memory requirement in elements
    """
    return m * n


# Matrix-vector multiplication utilities
def _mvm_flops(m: int, n: int) -> int:
    """
    Calculate FLOPS for matrix-vector multiplication.
    
    Args:
        m: Matrix rows (or number of slopes/outputs)
        n: Matrix columns (or number of actuators/inputs)
        
    Returns:
        int: Number of floating point operations
    """
    return 2 * m * n


def _mvm_mem(m: int, n: int) -> int:
    """
    Calculate memory for matrix-vector multiplication.
    
    Args:
        m: Matrix rows
        n: Matrix columns
        
    Returns:
        int: Memory requirement in elements
    """
    return 2 * m * n


# Matrix-matrix multiplication utilities
def _mmm_flops(m: int, n: int) -> int:
    """
    Calculate FLOPS for matrix-matrix multiplication.
    
    Args:
        m: First dimension size
        n: Second dimension size
        
    Returns:
        int: Number of floating point operations
    """
    return m * n


def _mmm_mem(m: int, n: int) -> int:
    """
    Calculate memory for matrix-matrix multiplication.
    
    Args:
        m: First dimension size
        n: Second dimension size
        
    Returns:
        int: Memory requirement in elements
    """
    return 2 * m * n


# Sorting operation utilities
def _merge_sort_flops(n: int) -> int:
    """
    Calculate FLOPS for merge sort operation.
    
    Args:
        n: Number of elements to sort
        
    Returns:
        int: Number of floating point operations
    """
    return 2 * n * np.log2(n)


def _merge_sort_mem(n: int) -> int:
    """
    Calculate memory for merge sort operation.
    
    Args:
        n: Number of elements to sort
        
    Returns:
        int: Memory requirement in elements
    """
    return 2 * n


# Square difference correlation utilities
def _square_diff_flops(m: int, n: int) -> int:
    """
    Calculate FLOPS for square difference operation.
    
    Used in extended source centroiding as an alternative to cross-correlation.
    
    Args:
        m: First dimension size
        n: Second dimension size
        
    Returns:
        int: Number of floating point operations
    """
    a = (2 * n**2) - 1
    b = m - n + 1
    return (a * (b**2)) + ((n**2) * (m - n + 1) ** 2)


def _square_diff_mem(m: int, n: int) -> int:
    """
    Calculate memory for square difference operation.
    
    Args:
        m: First dimension size
        n: Second dimension size
        
    Returns:
        int: Memory requirement in elements
    """
    return m**2 + n**2


# Calibration operation utilities
def _calibration_flops(n_pixels: int) -> int:
    """
    Calculate number of floating point operations for pixel calibration.
    
    Includes dark subtraction and flat field division operations.

    Args:
        n_pixels: Number of pixels to calibrate

    Returns:
        int: Number of floating point operations
    """
    # Operations: dark subtraction, flat field division
    return 2 * n_pixels


def _calibration_mem(n_pixels: int, bit_depth: int) -> int:
    """
    Calculate memory operations for pixel calibration.
    
    Includes reading raw pixel data, dark frame, flat field, and writing result.

    Args:
        n_pixels: Number of pixels to calibrate
        bit_depth: Bit depth of raw pixel data

    Returns:
        int: Number of memory operations in bits
    """
    # Read pixel, read dark, read flat, write calibrated pixel
    return bit_depth * n_pixels + 3 * n_pixels * 32


# Control operation utilities
def _integration_flops(m: int) -> int:
    """
    Calculate FLOPS for integration operation in control systems.
    
    Args:
        m: Number of elements (actuators)
        
    Returns:
        int: Number of floating point operations
    """
    return 2 * m


def _integration_mem(m: int) -> int:
    """
    Calculate memory for integration operation.
    
    Args:
        m: Number of elements (actuators)
        
    Returns:
        int: Memory requirement in elements
    """
    return 2 * m


def _pid_flops(m: int) -> int:
    """
    Calculate FLOPS for PID control operation.
    
    Includes proportional, integral, and derivative terms.
    
    Args:
        m: Number of control elements
        
    Returns:
        int: Number of floating point operations
    """
    return 6 * m


def _pid_mem(m: int) -> int:
    """
    Calculate memory for PID control operation.
    
    Args:
        m: Number of control elements
        
    Returns:
        int: Memory requirement in elements
    """
    return 2 * m


def _offset_flops(m: int) -> int:
    """
    Calculate FLOPS for offset computation.
    
    Args:
        m: Number of elements
        
    Returns:
        int: Number of floating point operations
    """
    return m


def _offset_mem(m: int) -> int:
    """
    Calculate memory for offset computation.
    
    Args:
        m: Number of elements
        
    Returns:
        int: Memory requirement in elements
    """
    return 2 * m


def _saturation_flops(m: int) -> int:
    """
    Calculate FLOPS for saturation handling (clamping values).
    
    Args:
        m: Number of elements
        
    Returns:
        int: Number of floating point operations
    """
    return 2 * m


def _saturation_mem(m: int) -> int:
    """
    Calculate memory for saturation handling.
    
    Args:
        m: Number of elements
        
    Returns:
        int: Memory requirement in elements
    """
    return 2 * m


def _dm_power_flops(m: int) -> int:
    """
    Calculate FLOPS for DM (deformable mirror) power estimation.
    
    Args:
        m: Number of actuators
        
    Returns:
        int: Number of floating point operations
    """
    return 2 * m


def _dm_power_mem(m: int) -> int:
    """
    Calculate memory for DM power estimation.
    
    Args:
        m: Number of actuators
        
    Returns:
        int: Memory requirement in elements
    """
    return 2 * m

