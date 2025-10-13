"""
Shack-Hartmann Utility Functions

This module contains utility functions for working with Shack-Hartmann wavefront sensors,
including functions to generate subaperture maps and extract subaperture images.
"""

import numpy as np


def genSHSubApMap(numSubApX, numSubApY, rIn, rOut, mask=True):
    """
    Generate subaperture map for Shack-Hartmann WFS

    Args:
        numSubApX (int): Number of subapertures along the direction X
        numSubApY (int): Number of subapertures along the direction Y
        rIn (float): Inner radius of the pupil image (unit: subapertures)
        rOut (float): Outer radius of the pupil image (unit: subapertures)
        mask (bool): If True, returns a mask (1's and 0's), otherwise numbers the subapertures

    Returns:
        numpy.ndarray: Generated subaperure map. If mask=False, subapertures are numbered
        by rows left-to-right and top-to-bottom, starting with index 1.
        The value 0 indicates a non-illuminated subaperture.
    """
    # Initialize subaperture map
    subApMap = np.zeros([numSubApY, numSubApX])

    # Calculate the center position
    c = [numSubApX / 2, numSubApY / 2]

    # Compute used subapertures as those whose center point is within the pupil
    # image - i.e. its distance to the center of the SH grid is within the
    # inner and outer pupil image radius.
    subApNum = 0
    for row in range(numSubApY):
        for col in range(numSubApX):
            # Subaperture center coordinates
            p = [col + 0.5, numSubApY - 1 - row + 0.5]
            # Distance to the center of the grid
            A = [0, 0]
            A[0] = p[0] - c[0]
            A[1] = p[1] - c[1]
            r = np.linalg.norm(A, 2)
            if r < rOut and r > rIn:
                subApNum += 1
                if mask:
                    subApMap[row, col] = 1
                else:
                    subApMap[row, col] = subApNum

    return subApMap


def extractSubAperture(
    pixelImage, subAperture, subApPix, nSubAps=0, offsetX=0, offsetY=0
):
    """
    Extract a subaperture from a pixel image

    Args:
        pixelImage (numpy.ndarray): Complete pixel image
        subAperture (int or tuple): Subaperture index (scalar) or coordinates (tuple)
        subApPix (int): Number of pixels per subaperture
        nSubAps (int): Number of subapertures along one dimension (required if subAperture is scalar)
        offsetX (int): X-axis offset in pixels
        offsetY (int): Y-axis offset in pixels

    Returns:
        numpy.ndarray: View of the subaperture pixels
    """
    # Get subaperture x,y co-ordinates
    if np.isscalar(subAperture):
        X = subAperture % nSubAps
        Y = subAperture // nSubAps
    elif len(subAperture) == 2:
        X = subAperture[1]
        Y = subAperture[0]
    else:
        raise TypeError("subAperture must be a scalar or tuple length 2")

    # Get first pixel in x and y including any x/y offsets
    startX = int(X * subApPix + offsetX)
    startY = int(Y * subApPix + offsetY)

    # Extract view onto subaperture from detector
    subAp = pixelImage[startY : (startY + subApPix), startX : (startX + subApPix)]
    return subAp


def genGaussSpot(size, width=3, centre=None):
    """
    Make a square gaussian kernel

    Generates sub-aperture image of size 'size' x 'size' containing a
    Gaussian spot of unity peak value and 1/e-width given by 'width'
    centered at specified location.

    Args:
        size (int): Sub-aperture size (in pixels)
        width (float): 1/e-width of the Gaussian spot to be generated
        centre (tuple): (X,Y) coordinates of the Gaussian spot centre (default: center of image)

    Returns:
        numpy.ndarray: Normalized sub-aperture image with Gaussian spot
    """
    x = np.arange(0, size, 1, float)
    y = x[:, np.newaxis]

    if centre is None:
        x0 = y0 = size // 2
    else:
        x0 = centre[0]
        y0 = centre[1]

    subApImg = np.exp(-4 * np.log(2) * ((x - x0) ** 2 + (y - y0) ** 2) / width**2)
    normalised_subApImage = subApImg / np.max(subApImg)

    return normalised_subApImage


def getAvailableSubAps(readoutMap, nPixels, nPixPerSubAp, pixelAgenda, subApMap):
    """
    Calculate which subapertures are available after each packet is received

    Args:
        readoutMap (numpy.ndarray): Map of pixel readout order (None for linear readout)
        nPixels (int): Total number of pixels along one dimension
        nPixPerSubAp (int): Number of pixels per subaperture along one dimension
        pixelAgenda (numpy.ndarray): Number of pixels received in each packet
        subApMap (numpy.ndarray): Subaperture map

    Returns:
        numpy.ndarray: Number of available subapertures after each packet
    """
    det = np.zeros([nPixels, nPixels])
    det_flat = det.reshape(nPixels * nPixels)

    nPackets = len(pixelAgenda)
    nTpixPerSub = nPixPerSubAp * nPixPerSubAp
    nValidSubAps = int(np.max(subApMap))
    availableSubAps = np.zeros(nPackets)
    nPackets = pixelAgenda.shape[0]
    listOfSubAps = []
    pixelsReceived = 0
    start_subAp = 0

    for i in range(nPackets):
        PerPacketList = []
        # Set the newly received pixels to 1
        start = pixelsReceived
        end = int(start + pixelAgenda[i])

        # If scramble map provided use it, otherwise assume linear
        if readoutMap is not None:
            for j in range(int(pixelAgenda[i])):
                det_flat[int(readoutMap[start + j])] = 1
        else:
            det_flat[start:end] += 1

        for j in range(start_subAp, nValidSubAps):
            subAp = np.where(subApMap == (j + 1))
            subApImg = extractSubAperture(det, subAp, nPixPerSubAp)

            if np.sum(subApImg) >= (nTpixPerSub):
                availableSubAps[i] += 1
                PerPacketList.append(j + 1)

        pixelsReceived += int(pixelAgenda[i])
        if PerPacketList:
            start_subAp = np.max(PerPacketList)

        listOfSubAps.append(PerPacketList)

    return availableSubAps
