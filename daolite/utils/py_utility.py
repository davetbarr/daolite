"""
pyramid WFS Utility Functions

This module contains utility functions for working with pyramid wavefront sensors,
including functions to generate pupil images and extract subaperture images and create agendas.
"""

import numpy as np


def generate_pyramid_pupil_image(shape, centres, radius):
    # Create a blank image (mask) filled with zeros
    mask = np.zeros(shape, dtype=np.uint8)

    # Get image dimensions
    h, w = shape

    # Create the mask with circles
    Y, X = np.ogrid[:h, :w]

    for center in centres:
        # Adjust center if too close to edge
        center_x_orig, center_y_orig = center

        # Ensure center_x is at least radius pixels from the edges
        center_x = max(radius, min(w - radius, center_x_orig))

        # Ensure center_y is at least radius pixels from the edges
        center_y = max(radius, min(h - radius, center_y_orig))

        if (center_x != center_x_orig) or (center_y != center_y_orig):
            print(
                f"Adjusted center from ({center_x_orig}, {center_y_orig}) to ({center_x}, {center_y}) to fit within image bounds."
            )

        # Create circle
        dist_from_center = (X - center_x) ** 2 + (Y - center_y) ** 2
        mask[dist_from_center <= radius**2] = 1
    return mask


def create_pupil_ids(newMask):
    # slope_map = createPupilIdMap(newMask)
    h, w = newMask.shape
    slopeMap = np.zeros((int(np.sum(newMask)) // 4, 4))

    print(
        f"createPupilIdMap: newMask shape = {newMask.shape}, total valid pixels = {np.sum(newMask)}"
    )

    q1 = np.copy(newMask[0 : h // 2, 0 : w // 2]).astype(np.int32)
    q2 = np.copy(newMask[0 : h // 2, w // 2 : w]).astype(np.int32)
    q3 = np.copy(newMask[h // 2 : h, 0 : w // 2]).astype(np.int32)
    q4 = np.copy(newMask[h // 2 : h, w // 2 : w]).astype(np.int32)

    q1flat = q1.flatten()
    q2flat = q2.flatten()
    q3flat = q3.flatten()
    q4flat = q4.flatten()

    print(
        f"Quadrant valid pixel counts: Q1={np.sum(q1flat==1)}, Q2={np.sum(q2flat==1)}, Q3={np.sum(q3flat==1)}, Q4={np.sum(q4flat==1)}"
    )

    count = 1
    for i in range(q1flat.size):
        if q1flat[i] == 1:
            q1flat[i] = count
            count += 1
    print(f"Q1 IDs assigned up to {count-1}")
    count = 1
    for i in range(q2flat.size):
        if q2flat[i] == 1:
            q2flat[i] = count
            count += 1
    print(f"Q2 IDs assigned up to {count-1}")
    count = 1
    for i in range(q3flat.size):
        if q3flat[i] == 1:
            q3flat[i] = count
            count += 1
    print(f"Q3 IDs assigned up to {count-1}")
    count = 1
    for i in range(q4flat.size):
        if q4flat[i] == 1:
            q4flat[i] = count
            count += 1
    print(f"Q4 IDs assigned up to {count-1}")

    # glue the quadrants back together
    q1 = q1flat.reshape(q1.shape)
    q2 = q2flat.reshape(q2.shape)
    q3 = q3flat.reshape(q3.shape)
    q4 = q4flat.reshape(q4.shape)

    slope_map_full = np.zeros(newMask.shape, dtype=int)
    slope_map_full[0 : h // 2, 0 : w // 2] = np.copy(q1)
    slope_map_full[0 : h // 2, w // 2 : w] = np.copy(q2)
    slope_map_full[h // 2 : h, 0 : w // 2] = np.copy(q3)
    slope_map_full[h // 2 : h, w // 2 : w] = np.copy(q4)

    print(f"slope_map_full unique IDs: {np.unique(slope_map_full)}")

    # Find all IDs that exist in all four quadrants and only include those with exactly four valid pixels
    unique_ids = np.unique(slope_map_full)
    valid_ids = []
    valid_indices = []
    for uid in unique_ids:
        if uid == 0:
            continue
        A = np.where(slope_map_full == uid)
        if len(A[0]) == 4:
            indices = [A[0][j] * slope_map_full.shape[1] + A[1][j] for j in range(4)]
            if all(newMask.flatten()[idx] == 1 for idx in indices):
                valid_ids.append(uid)
                valid_indices.append(indices)

    slopeMap = np.zeros((len(valid_ids), 4))
    # print(f"IDs present in all 4 quadrants with valid pixels: {valid_ids}")
    for i, indices in enumerate(valid_indices):
        for j in range(4):
            slopeMap[i, j] = indices[j]
    # print(f"Final slopeMap:\n{slopeMap}")
    return slopeMap


def calculate_centroid_agenda(packet_map, pupil_id):
    """
    Determine when each subaperture becomes available for centroid calculation
    Args:
        packet_map (np.ndarray): Array mapping packets to subapertures
        .
        pupil_id (np.ndarray): Array of pupil IDs for subapertures.
        Returns:
        np.ndarray: Array indicating the number of subapertures to process at each iteration.
        n_subapertures = pupil_id.shape[0]
    """

    # pupils_ids shape: (n_subapertures, 4)
    # when all the pixels for a given pupil_id are available in packet_map, that pupil can be processed
    n_subapertures = pupil_id.shape[0]
    max_packet_index = np.max(packet_map) + 1
    print(
        f"calculate_centroid_agenda: n_subapertures = {n_subapertures}, max_packet_index = {max_packet_index}"
    )
    centroid_agenda = np.zeros(max_packet_index, dtype=int)

    # Track which subapertures have been completed
    completed = np.zeros(n_subapertures, dtype=bool)

    # For each packet, check which subapertures become complete
    for packet_num in range(max_packet_index):
        for subap_idx in range(n_subapertures):
            if completed[subap_idx]:
                continue

            # Check if all pixels in this subaperture have been received
            # (i.e., their packet number <= current packet)
            pixel_indices = pupil_id[subap_idx, :].astype(int)
            subap_region = packet_map[pixel_indices]
            print(
                f"Packet {packet_num}: Checking subaperture {subap_idx} with pixels {subap_region}"
            )

            if np.all(subap_region <= packet_num):
                centroid_agenda[packet_num] += 1
                completed[subap_idx] = True
        print(
            f"After packet {packet_num}, centroid_agenda: {centroid_agenda}, completed: {completed}"
        )

    # Verify we found all subapertures
    assert (
        np.sum(centroid_agenda) == n_subapertures
    ), f"Centroid agenda sum ({np.sum(centroid_agenda)}) doesn't match number of subapertures ({n_subapertures})"

    return centroid_agenda


def calculate_centroid_intensity_agenda(packet_map, pupil_id):
    """
    Determine when each subaperture becomes available for centroid calculation
    Args:
        packet_map (np.ndarray): Array mapping packets to subapertures
        pupil_id (np.ndarray): Array of pupil IDs for subapertures.
    Returns:
        np.ndarray: Array indicating the number of subapertures to process at each iteration.
    """

    # pupils_ids shape: (n_subapertures, 4)
    # all pixels for a given pupil_id are independent subapertures in intensity mode
    pupil_id = pupil_id.flatten()
    n_subapertures = pupil_id.shape[0]
    max_packet_index = np.max(packet_map) + 1
    print(
        f"calculate_centroid_intensity_agenda: n_subapertures = {n_subapertures}, max_packet_index = {max_packet_index}"
    )
    centroid_agenda = np.zeros(max_packet_index, dtype=int)

    # Track which subapertures have been completed
    completed = np.zeros(n_subapertures, dtype=bool)

    # For each packet, check which subapertures become complete
    for packet_num in range(max_packet_index):
        for subap_idx in range(n_subapertures):
            if completed[subap_idx]:
                continue

            # Check if all pixels in this subaperture have been received
            # (i.e., their packet number <= current packet)
            pixel_indices = pupil_id[subap_idx].astype(int)
            subap_region = packet_map[pixel_indices]
            print(
                f"Packet {packet_num}: Checking subaperture {subap_idx} with pixels {subap_region}"
            )

            if np.all(subap_region <= packet_num):
                centroid_agenda[packet_num] += 1
                completed[subap_idx] = True
        print(
            f"After packet {packet_num}, centroid_agenda: {centroid_agenda}, completed: {completed}"
        )

    # Verify we found all subapertures
    assert (
        np.sum(centroid_agenda) == n_subapertures
    ), f"Centroid agenda sum ({np.sum(centroid_agenda)}) doesn't match number of subapertures ({n_subapertures})"

    return centroid_agenda
