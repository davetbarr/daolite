from daolite.gui.designer.pipeline_designer import PipelineDesignerApp

def _estimate_data_size(self, src_comp, dest_comp):
    """
    Estimate the data size transferred between components based on their types.
    
    Args:
        src_comp: Source component
        dest_comp: Destination component
        
    Returns:
        int: Estimated data size in bits
    """
    # Default size
    data_size = 1024 * 1024 * 8  # 1MB in bits
    
    # Extract parameters with realistic defaults for AO systems
    if src_comp.component_type == ComponentType.CAMERA:
        # Camera typically outputs pixel data
        if "n_pixels" in src_comp.params:
            n_pixels = src_comp.params["n_pixels"]
        elif "n_subapertures" in src_comp.params and "pixels_per_subaperture" in src_comp.params:
            n_pixels = src_comp.params["n_subapertures"] * src_comp.params["pixels_per_subaperture"]
        else:
            # Default: 80×80 subapertures with 16×16 pixels each for ELT-scale
            n_pixels = 6400 * 256
        
        bit_depth = src_comp.params.get("bit_depth", 16)
        data_size = n_pixels * bit_depth
        logger.debug(f"Estimated camera data size: {n_pixels} pixels × {bit_depth} bits = {data_size} bits")
            
    elif src_comp.component_type == ComponentType.CENTROIDER:
        # Centroider outputs slopes (X and Y for each subaperture)
        if "n_subapertures" in src_comp.params:
            n_subaps = src_comp.params["n_subapertures"]
        elif "n_subaps" in src_comp.params:
            n_subaps = src_comp.params["n_subaps"]
        else:
            # Default: 80×80 = 6400 subapertures (typical for ELT-scale AO)
            n_subaps = 6400
        
        # Each subaperture has X and Y slopes, typically floating point (32 bits)
        precision = src_comp.params.get("output_precision", "float")
        bit_size = 64 if precision == "double" else 32  # float32 or float64
        data_size = n_subaps * 2 * bit_size
        logger.debug(f"Estimated centroider data size: {n_subaps} subaps × 2 slopes × {bit_size} bits = {data_size} bits")
            
    elif src_comp.component_type == ComponentType.RECONSTRUCTION:
        # Reconstruction outputs actuator commands
        if "n_actuators" in src_comp.params:
            n_actuators = src_comp.params["n_actuators"]
        elif "n_modes" in src_comp.params:
            # If using modal control, output size is based on number of modes
            n_actuators = src_comp.params["n_modes"]
        else:
            # Default: 5000-6000 actuators (typical for ELT-scale AO)
            n_actuators = 5000
        
        # Each actuator command is typically floating point (32 bits)
        precision = src_comp.params.get("output_precision", "float")
        bit_size = 64 if precision == "double" else 32
        data_size = n_actuators * bit_size
        logger.debug(f"Estimated reconstruction data size: {n_actuators} actuators × {bit_size} bits = {data_size} bits")
            
    elif src_comp.component_type == ComponentType.CALIBRATION:
        # Calibration typically outputs calibrated pixel data
        if "n_pixels" in src_comp.params:
            n_pixels = src_comp.params["n_pixels"]
        elif "n_subapertures" in src_comp.params and "pixels_per_subaperture" in src_comp.params:
            n_pixels = src_comp.params["n_subapertures"] * src_comp.params["pixels_per_subaperture"]
        else:
            # Default for ELT-scale WFS
            n_pixels = 6400 * 256
            
        # Usually same bit depth as input but could be floating point
        output_format = src_comp.params.get("output_format", "same")
        if output_format == "float":
            bit_depth = 32
        elif output_format == "double":
            bit_depth = 64
        elif output_format == "uint16":
            bit_depth = 16
        elif output_format == "uint8":
            bit_depth = 8
        else:  # "same" or unspecified
            bit_depth = 16  # Default to 16-bit pixels
            
        data_size = n_pixels * bit_depth
        logger.debug(f"Estimated calibration data size: {n_pixels} pixels × {bit_depth} bits = {data_size} bits")
            
    elif src_comp.component_type == ComponentType.CONTROL:
        # Control may output augmented actuator commands or telemetry
        if "n_actuators" in src_comp.params:
            n_actuators = src_comp.params["n_actuators"]
        elif "n_modes" in src_comp.params:
            n_actuators = src_comp.params["n_modes"]
        else:
            # Default: 5000-6000 actuators (typical for ELT-scale AO)
            n_actuators = 5000
            
        # Include additional telemetry data (e.g., diagnostics, timing)
        telemetry_enabled = src_comp.params.get("telemetry_enabled", False)
        telemetry_multiplier = src_comp.params.get("telemetry_factor", 1.0)
        
        # If telemetry is enabled, add overhead for diagnostic data
        if telemetry_enabled:
            telemetry_multiplier = max(telemetry_multiplier, 1.5)  # At least 50% overhead for telemetry
            
        precision = src_comp.params.get("output_precision", "float")
        bit_size = 64 if precision == "double" else 32
        
        data_size = int(n_actuators * bit_size * telemetry_multiplier)
        logger.debug(f"Estimated control data size: {n_actuators} actuators × {bit_size} bits × {telemetry_multiplier} = {data_size} bits")
    
    # If source component estimation didn't work, try using destination component
    if data_size <= 0:
        logger.debug(f"Source component data size estimation failed, trying destination component")
        if dest_comp.component_type == ComponentType.CENTROIDER:
            # Input to centroider is pixel data
            if "n_subapertures" in dest_comp.params and "pixels_per_subaperture" in dest_comp.params:
                n_pixels = dest_comp.params["n_subapertures"] * dest_comp.params["pixels_per_subaperture"]
            elif "n_subaps" in dest_comp.params and "pixels_per_subap" in dest_comp.params:
                n_pixels = dest_comp.params["n_subaps"] * dest_comp.params["pixels_per_subap"]
            else:
                # Default: 80×80 subapertures with 16×16 pixels
                n_pixels = 6400 * 256
                
            # Input bit depth, commonly 12-16 bits for scientific cameras
            bit_depth = dest_comp.params.get("input_bit_depth", 16)
            data_size = n_pixels * bit_depth
            logger.debug(f"Estimated data size from centroider input: {n_pixels} pixels × {bit_depth} bits = {data_size} bits")
                
        elif dest_comp.component_type == ComponentType.RECONSTRUCTION:
            # Input to reconstruction is slopes
            if "n_slopes" in dest_comp.params:
                n_slopes = dest_comp.params["n_slopes"]
            elif "n_subapertures" in dest_comp.params:
                n_slopes = dest_comp.params["n_subapertures"] * 2  # X and Y slopes
            elif "n_subaps" in dest_comp.params:
                n_slopes = dest_comp.params["n_subaps"] * 2  # X and Y slopes
            else:
                # Default: 80×80 = 6400 subapertures, each with X and Y
                n_slopes = 6400 * 2
                
            precision = dest_comp.params.get("input_precision", "float")
            bit_size = 64 if precision == "double" else 32
            data_size = n_slopes * bit_size
            logger.debug(f"Estimated data size from reconstruction input: {n_slopes} slopes × {bit_size} bits = {data_size} bits")
                
        elif dest_comp.component_type == ComponentType.CONTROL:
            # Input to control is actuator commands
            if "n_actuators" in dest_comp.params:
                n_actuators = dest_comp.params["n_actuators"]
            elif "n_modes" in dest_comp.params:
                n_actuators = dest_comp.params["n_modes"]
            else:
                # Default: 5000 actuators (typical for ELT-scale DM)
                n_actuators = 5000
                
            precision = dest_comp.params.get("input_precision", "float")
            bit_size = 64 if precision == "double" else 32
            data_size = n_actuators * bit_size
            logger.debug(f"Estimated data size from control input: {n_actuators} actuators × {bit_size} bits = {data_size} bits")
            
        # Check for calibration input
        elif dest_comp.component_type == ComponentType.CALIBRATION:
            # Input to calibration is typically raw pixel data
            if "n_pixels" in dest_comp.params:
                n_pixels = dest_comp.params["n_pixels"]
            elif "n_subapertures" in dest_comp.params and "pixels_per_subaperture" in dest_comp.params:
                n_pixels = dest_comp.params["n_subapertures"] * dest_comp.params["pixels_per_subaperture"]
            else:
                # Default: 80×80 subapertures with 16×16 pixels
                n_pixels = 6400 * 256
                
            # Raw pixel data is typically 12-16 bit
            bit_depth = dest_comp.params.get("input_bit_depth", 16)
            data_size = n_pixels * bit_depth
            logger.debug(f"Estimated data size from calibration input: {n_pixels} pixels × {bit_depth} bits = {data_size} bits")
    
    # Set minimum data size to ensure small transfers are still represented
    min_data_size = 1024  # 1 kilobit minimum
    
    # Apply header overhead (control data, timestamps, etc.)
    header_size = 256 * 8  # 256 bytes header
    
    return max(data_size + header_size, min_data_size)

if __name__ == "__main__":
    PipelineDesignerApp.run()
