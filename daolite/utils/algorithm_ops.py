"""
Algorithm operation utilities for computing FLOPS and memory requirements.

This module provides utility functions to calculate the computational complexity
(FLOPS) and memory requirements for common algorithms used in adaptive optics
systems, such as FFT, matrix operations, sorting, and correlation algorithms.
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
        m: Matrix rows
        n: Matrix columns (vector size)
        
    Returns:
        int: Number of floating point operations
    """
    return 2 * m * n


def _mvm_mem(m: int, n: int) -> int:
    """
    Calculate memory for matrix-vector multiplication.
    
    Args:
        m: Matrix rows
        n: Matrix columns (vector size)
        
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
