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


def readout_by_pixel_agenda(readout_pattern, pixel_agenda):
    """
    Map pixels to packet numbers based on readout order and pixel agenda

    Args:
        readout_pattern (numpy.ndarray): 2D array showing readout order for each pixel
        pixel_agenda (numpy.ndarray): 2D array [nPackets x 2] where each row is [packet_number, pixels_in_packet]

    Returns:
        numpy.ndarray: 2D array same shape as readout_pattern, with packet numbers for each pixel
    """
    packet_map = np.zeros_like(readout_pattern)

    # Convert pixel_agenda to cumulative pixels received
    cumulative_pixels = np.cumsum(pixel_agenda[:, 1])
    cumulative_pixels = np.insert(cumulative_pixels, 0, 0)  # Add 0 at the beginning

    # For each packet, mark which pixels belong to it
    for i in range(len(pixel_agenda)):
        start_pixel = cumulative_pixels[i]
        end_pixel = cumulative_pixels[i + 1]

        # Find all pixels with readout order in this range
        mask = (readout_pattern >= start_pixel) & (readout_pattern < end_pixel)
        packet_map[mask] = i

    return packet_map


def getSubApCentrePoints(subApMap, subApPix, width, height, guardPixels):
    """
    Calculate pixel coordinates of subaperture centers

    Args:
        subApMap (numpy.ndarray): 2D array showing subaperture layout
        subApPix (int): Number of pixels per subaperture along one dimension
        width (int): Total image width in pixels
        height (int): Total image height in pixels
        guardPixels (int): Number of guard pixels around subapertures

    Returns:
        numpy.ndarray: Array of [x, y] coordinates for each subaperture center
    """
    nSubAps = int(np.max(subApMap))
    centres = np.zeros((nSubAps, 2))

    # Get the dimensions of the subaperture map
    map_height, map_width = subApMap.shape

    # Calculate scaling factors from map coordinates to pixel coordinates
    scale_x = width / map_width
    scale_y = height / map_height

    # Find center of each subaperture
    for i in range(nSubAps):
        # Find position in the map (map coordinates are row, col)
        positions = np.where(subApMap == (i + 1))

        if len(positions[0]) > 0:
            # Get the first occurrence (there should only be one per subaperture)
            map_row = positions[0][0]
            map_col = positions[1][0]

            # Convert from map coordinates to pixel coordinates
            # Add 0.5 to get center of the map cell, then scale
            pixel_x = (map_col + 0.5) * scale_x
            pixel_y = (map_row + 0.5) * scale_y

            centres[i] = [pixel_x, pixel_y]

    return centres


def calculate_centroid_agenda(packet_map, centres, subApPix):
    """
    Determine when each subaperture becomes available for centroid calculation

    Args:
        packet_map (numpy.ndarray): 2D array with packet number for each pixel
        centres (numpy.ndarray): Array of [x, y] coordinates for subaperture centers
        subApPix (int): Number of pixels per subaperture along one dimension

    Returns:
        numpy.ndarray: Number of centroids that can be calculated after each packet
    """
    nPackets = int(np.max(packet_map)) + 1
    nSubAps = len(centres)
    centroid_agenda = np.zeros(nPackets, dtype=int)

    half_subap = subApPix / 2.0

    # Track which subapertures have been completed
    completed = np.zeros(nSubAps, dtype=bool)

    # For each packet, check which subapertures become complete
    for packet_num in range(nPackets):
        for subap_idx in range(nSubAps):
            if completed[subap_idx]:
                continue

            # Get the subaperture bounds
            cx, cy = centres[subap_idx]
            x_min = int(cx - half_subap)
            x_max = int(cx + half_subap)
            y_min = int(cy - half_subap)
            y_max = int(cy + half_subap)

            # Check if all pixels in this subaperture have been received
            # (i.e., their packet number <= current packet)
            subap_region = packet_map[y_min:y_max, x_min:x_max]

            if np.all(subap_region <= packet_num):
                centroid_agenda[packet_num] += 1
                completed[subap_idx] = True

    # Verify we found all subapertures
    assert (
        np.sum(centroid_agenda) == nSubAps
    ), f"Centroid agenda sum ({np.sum(centroid_agenda)}) doesn't match number of subapertures ({nSubAps})"

    return centroid_agenda
