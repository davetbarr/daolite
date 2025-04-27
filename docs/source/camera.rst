.. _camera:

Camera Simulation
=================

.. _camera_overview:

Overview
--------

The camera simulation component in daolite (**D**\ urham **A**\ daptive **O**\ ptics **L**\ atency **I**\ nspection and **T**\ iming **E**\ stimator) models the behavior and timing of wavefront sensor cameras in adaptive optics systems. daolite provides detailed timing models for various camera readout patterns, frame rates, and data transfer mechanisms to accurately estimate the initial latency component in AO systems.

.. _camera_features:

Key Camera Features
-------------------

* **Detector Readout**: Models various readout patterns and speeds
* **Frame Transfer**: Simulates parallel and serial readout modes
* **Packetization**: Models camera data packetization for streaming
* **Interface Timing**: Simulates various camera interfaces (Camera Link, GigE Vision, etc.)
* **Region of Interest (ROI)**: Models the effect of ROI selection on readout time
* **Binning**: Simulates on-chip binning effects on readout speed
* **Triggered Operation**: Models triggered and free-running camera modes

.. _using_camera:

Using Camera Components
-----------------------

Adding a camera simulator to your AO pipeline is straightforward:

.. code-block:: python

    from daolite import Pipeline, PipelineComponent, ComponentType
    from daolite.simulation.camera import PCOCamLink
    from daolite import amd_epyc_7763
    
    # Create a pipeline
    pipeline = Pipeline()
    
    # Define a CPU resource for camera simulation
    cpu = amd_epyc_7763()
    
    # Add camera component
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.CAMERA,
        name="WFS Camera",
        compute=cpu,
        function=PCOCamLink,
        params={
            "n_pixels": 1024*1024,  # 1 megapixel camera
            "readout_mode": "global",  # Global shutter
            "bit_depth": 12,  # 12-bit ADC
            "frame_rate": 1000  # 1000 Hz
        }
    ))

.. _camera_configuration:

Camera Configuration
--------------------

Camera components accept various parameters to customize their behavior:

.. code-block:: python

    params={
        # Required parameters
        "n_pixels": 1024*1024,  # Total number of pixels
        
        # Optional parameters
        "readout_mode": "global",  # "global", "rolling", "frame-transfer"
        "bit_depth": 12,  # ADC bit depth
        "frame_rate": 1000,  # Hz
        "exposure_time": 800,  # μs
        "readout_time": 200,  # μs
        "interface": "cameralink",  # "cameralink", "gige", "usb3", "coaxpress"
        "bandwidth": 800e6,  # Interface bandwidth in bits/second
        "packetization": True,  # Enable packetized data transmission
        "group_size": 64,  # Number of packets per group
        "use_roi": False,  # Use Region of Interest
        "roi_width": 512,  # ROI width in pixels
        "roi_height": 512,  # ROI height in pixels
        "binning": 1,  # On-chip binning factor
    }

.. _camera_models:

Available Camera Models
-----------------------

daolite provides timing models for the following camera readout methods:

.. _global_shutter:

Global Shutter Readout
~~~~~~~~~~~~~~~~~~~~~~

Models cameras where all pixels are exposed simultaneously and then read out:

.. code-block:: python

    from daolite.simulation.camera import PCOCamLink
    
    # Use as a standalone function
    timing = PCOCamLink(
        compute=cpu,
        n_pixels=1024*1024,
        bit_depth=12,
        frame_rate=1000,
        debug=True
    )
    
    # Or in a pipeline component
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.CAMERA,
        name="Global Shutter WFS",
        compute=cpu,
        function=PCOCamLink,
        params={
            "n_pixels": 1024*1024,
            "bit_depth": 12,
            "frame_rate": 1000
        }
    ))

.. _rolling_shutter:

Rolling Shutter Readout
~~~~~~~~~~~~~~~~~~~~~~~

Models cameras where rows are exposed and read out sequentially:

.. code-block:: python

    from daolite.simulation.camera import RollingShutterCamera
    
    # Add as a pipeline component
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.CAMERA,
        name="Rolling Shutter WFS",
        compute=cpu,
        function=RollingShutterCamera,
        params={
            "n_pixels": 1024*1024,
            "bit_depth": 12,
            "frame_rate": 1000,
            "row_readout_time": 10  # μs per row
        }
    ))

.. _frame_transfer:

Frame Transfer Readout
~~~~~~~~~~~~~~~~~~~~~~

Models frame transfer CCDs where the image area is rapidly shifted to a storage area:

.. code-block:: python

    from daolite.simulation.camera import frame_transfer_readout
    
    # Add as a pipeline component
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.CAMERA,
        name="Frame Transfer WFS",
        compute=cpu,
        function=frame_transfer_readout,
        params={
            "n_pixels": 1024*1024,
            "bit_depth": 12,
            "frame_rate": 1000,
            "transfer_time": 50,  # μs for frame transfer
            "parallel_transfer_lines": 1  # Lines transferred in parallel
        }
    ))

.. _packetized_readout:

Packetized Readout
~~~~~~~~~~~~~~~~~~

Models cameras that stream data in packets for processing before the full frame is read:

.. code-block:: python

    from daolite.simulation.camera import packetized_readout
    
    # Add as a pipeline component
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.CAMERA,
        name="Packetized WFS",
        compute=cpu,
        function=packetized_readout,
        params={
            "n_pixels": 1024*1024,
            "bit_depth": 12,
            "frame_rate": 1000,
            "packet_size": 1024,  # Bytes per packet
            "group_size": 64,  # Packets per group
            "protocol_overhead": 36  # Bytes of protocol overhead per packet
        }
    ))

.. _roi_readout:

Region of Interest Readout
~~~~~~~~~~~~~~~~~~~~~~~~~~

Models cameras reading out only a portion of the sensor:

.. code-block:: python

    from daolite.simulation.camera import roi_readout
    
    # Add as a pipeline component
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.CAMERA,
        name="ROI WFS",
        compute=cpu,
        function=roi_readout,
        params={
            "n_pixels": 1024*1024,  # Full sensor size
            "bit_depth": 12,
            "frame_rate": 1000,
            "roi_width": 512,  # ROI width
            "roi_height": 512,  # ROI height
            "roi_x": 256,  # ROI top-left X
            "roi_y": 256  # ROI top-left Y
        }
    ))

.. _flexible_camera:

Flexible Camera Model
~~~~~~~~~~~~~~~~~~~~~

For convenience, daolite provides a combined camera function that can simulate various configurations:

.. code-block:: python

    from daolite.simulation.camera import PCOCamLink, GigeVisionCamera, RollingShutterCamera
    
    # Add flexible camera to the pipeline
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.CAMERA,
        name="Flexible WFS Camera",
        compute=cpu,
        function=PCOCamLink,
        params={
            "n_pixels": 1024*1024,
            "readout_mode": "global",  # "global", "rolling", "frame-transfer"
            "bit_depth": 12,
            "frame_rate": 1000,
            "packetization": True,
            "group_size": 64,
            "interface": "cameralink",
            "use_roi": True,
            "roi_width": 512,
            "roi_height": 512
        }
    ))

.. _camera_performance:

Performance Considerations
--------------------------

The computational cost and latency of camera operations depends on several factors:

* **Pixel Count**: Total number of pixels to read out
* **Readout Mode**: Global, rolling, or frame-transfer readout patterns
* **Frame Rate**: Higher frame rates reduce exposure and readout times
* **Interface Bandwidth**: Maximum data transfer rate
* **Packetization**: Overhead from packet headers and protocol
* **ROI Size**: Smaller regions of interest reduce readout time
* **Binning**: On-chip binning can reduce readout time

.. _roi_binning:

Modeling ROI and Binning Effects
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

daolite accurately models how ROI and binning settings affect frame rate and latency:

.. code-block:: python

    # Configure camera with ROI and binning
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.CAMERA,
        name="ROI and Binning",
        compute=cpu,
        function=PCOCamLink,
        params={
            "n_pixels": 2048*2048,  # Full frame
            "readout_mode": "global",
            "bit_depth": 12,
            "frame_rate": 500,  # Base frame rate
            "use_roi": True,
            "roi_width": 512,
            "roi_height": 512,
            "binning": 2,  # 2x2 binning
            "calculated_frame_rate": True  # Calculate max frame rate based on settings
        }
    ))

.. _interface_timing:

Interface Timing Models
~~~~~~~~~~~~~~~~~~~~~~~

daolite models various camera interfaces and their timing characteristics:

.. code-block:: python

    # Camera Link interface timing
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.CAMERA,
        name="CameraLink Full",
        compute=cpu,
        function=PCOCamLink,
        params={
            "n_pixels": 1024*1024,
            "bit_depth": 12,
            "interface": "cameralink_full",
            "bandwidth": 6.8e9,  # 6.8 Gbps for CameraLink Full
            "protocol_overhead": 0.05  # 5% overhead
        }
    ))
    
    # GigE Vision interface timing
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.CAMERA,
        name="GigE Vision WFS",
        compute=cpu,
        function=GigeVisionCamera,
        params={
            "n_pixels": 1024*1024,
            "bit_depth": 12,
            "frame_rate": 1000,
            "interface": "gige"
        }
    ))
    
    # CoaXPress interface timing
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.CAMERA,
        name="CoaXPress",
        compute=cpu,
        function=PCOCamLink,
        params={
            "n_pixels": 1024*1024,
            "bit_depth": 12,
            "interface": "coaxpress",
            "bandwidth": 12.5e9,  # 12.5 Gbps (CXP-12)
            "protocol_overhead": 0.02  # 2% overhead
        }
    ))

.. _custom_camera:

Customizing Camera Models
-------------------------

daolite allows you to create custom camera models with your own timing characteristics:

.. code-block:: python

    def custom_camera_model(compute, n_pixels, frame_rate=1000, extra_param=1.0, debug=False):
        """
        Custom camera timing model.
        
        Args:
            compute: Compute resource
            n_pixels: Number of pixels
            frame_rate: Frame rate in Hz
            extra_param: Custom scaling parameter
            debug: Enable debug output
            
        Returns:
            Numpy array with timing information
        """
        # Calculate base exposure and readout times
        frame_period = 1e6 / frame_rate  # μs
        exposure_ratio = 0.8  # 80% of frame period for exposure
        exposure_time = frame_period * exposure_ratio
        readout_time = frame_period * (1 - exposure_ratio)
        
        # Calculate data transfer time
        bits_per_pixel = 12
        bytes_per_frame = n_pixels * bits_per_pixel / 8
        interface_bandwidth = 6.8e9 / 8  # CameraLink Full in bytes/sec
        transfer_time = bytes_per_frame / interface_bandwidth * 1e6  # μs
        
        # Apply custom scaling
        readout_time *= extra_param
        transfer_time *= extra_param
        
        # Total frame time (can't exceed frame period)
        total_frame_time = min(frame_period, max(readout_time, transfer_time))
        
        if debug:
            print(f"Frame period: {frame_period:.2f} μs")
            print(f"Exposure time: {exposure_time:.2f} μs")
            print(f"Readout time: {readout_time:.2f} μs")
            print(f"Transfer time: {transfer_time:.2f} μs")
            print(f"Total frame time: {total_frame_time:.2f} μs")
        
        # Create timing array for simulation
        # We create one timing entry for each packet group
        n_groups = 10  # Example: divide into 10 groups
        timing = np.zeros([n_groups, 2])
        
        # Set start and end times for each group
        for i in range(n_groups):
            # Start time is proportional to group index
            timing[i, 0] = i * (total_frame_time / n_groups)
            # End time includes the group processing time
            timing[i, 1] = (i + 1) * (total_frame_time / n_groups)
        
        return timing
    
    # Use custom camera model in a pipeline
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.CONTROLLER,
        name="Custom Camera",
        compute=cpu,
        function=custom_camera_model,
        params={
            "n_pixels": 1024*1024,
            "frame_rate": 1000,
            "extra_param": 1.2,
            "debug": True
        }
    ))

.. _camera_applications:

Real-World Applications
-----------------------

Example: High-Speed WFS Camera
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Camera configuration for a high-speed wavefront sensor:

.. code-block:: python

    # High-speed WFS camera for ExAO
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.CAMERA,
        name="ExAO WFS Camera",
        compute=cpu,
        function=PCOCamLink,
        params={
            "n_pixels": 240*240,  # Small format sensor
            "readout_mode": "frame-transfer",
            "bit_depth": 10,  # Lower bit depth for speed
            "frame_rate": 3000,  # 3 kHz frame rate
            "interface": "cameralink_full",
            "packetization": True,
            "group_size": 32,
            "use_roi": True,
            "roi_width": 160,
            "roi_height": 160
        }
    ))

Example: Large-Format Solar WFS
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Camera configuration for a large-format solar wavefront sensor:

.. code-block:: python

    # Large-format solar WFS
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.CAMERA,
        name="Solar WFS Camera",
        compute=cpu,
        function=PCOCamLink,
        params={
            "n_pixels": 2048*2048,  # Large format sensor
            "readout_mode": "global",
            "bit_depth": 12,
            "frame_rate": 1500,  # 1.5 kHz frame rate
            "interface": "coaxpress",
            "bandwidth": 25e9,  # Dual CXP-12 (25 Gbps)
            "packetization": True,
            "group_size": 128
        }
    ))

Example: Multi-ROI Readout
~~~~~~~~~~~~~~~~~~~~~~~~~~

Camera configuration for a wavefront sensor using multiple regions of interest:

.. code-block:: python

    # Multi-ROI readout
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.CAMERA,
        name="Multi-ROI WFS",
        compute=cpu,
        function=multi_roi_readout,
        params={
            "n_pixels": 1024*1024,  # Full sensor
            "bit_depth": 12,
            "frame_rate": 2000,  # 2 kHz frame rate
            "rois": [
                {"x": 100, "y": 100, "width": 128, "height": 128},
                {"x": 400, "y": 400, "width": 128, "height": 128},
                {"x": 700, "y": 700, "width": 128, "height": 128}
            ],
            "interface": "cameralink_medium"
        }
    ))

.. _camera_troubleshooting:

Troubleshooting
---------------

Common issues and solutions:

* **Bandwidth Limitations**:
  - Reduce bit depth or frame rate
  - Use ROI to read out smaller regions
  - Apply on-chip binning
  - Use a faster interface (CoaXPress instead of GigE Vision)
  
* **Exposure/Frame Rate Tradeoffs**:
  - Use frame transfer mode to minimize dead time
  - Consider specialized fast readout modes
  - Use partial readout techniques
  
* **Latency Issues**:
  - Enable packetization for earlier processing of partial frames
  - Optimize packet and group sizes
  - Use ROIs targeted to specific areas of interest
  - Consider triggered vs. free-running mode based on synchronization needs

.. _related_topics_camera:

Related Topics
--------------

* :ref:`centroider` - Processing camera images for wavefront sensing
* :ref:`calibration` - Calibration procedures for camera data
* :ref:`network` - Data transfer from cameras to processing units
* :ref:`latency_model` - Understanding timing and latency in AO systems

.. _camera_api_reference:

API Reference
-------------

For complete API details, see the :ref:`api_camera` section.

.. seealso::
   
   * :ref:`camera_performance` - For detailed information on camera timing 
   * :ref:`camera_applications` - For practical camera configuration examples
   * :ref:`pipeline` - Integration of cameras into the complete AO pipeline