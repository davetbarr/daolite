.. _network:

Network and Data Transfer
=========================

Overview
--------

The network and data transfer component in DaoLITE (**D**\ urham **A**\ daptive **O**\ ptics **L**\ atency **I**\ nspection and **T**\ iming **E**\ stimator) models the latency associated with moving data between different hardware elements in adaptive optics systems. DaoLITE provides detailed timing models for various network technologies, PCIe transfers, and other data movement operations that significantly impact overall AO system latency.

Key Data Transfer Features
--------------------------

* **Network Communication**: Models Ethernet, InfiniBand, RoCE, and other network technologies
* **PCIe Transfer**: Simulates data movement between CPU and GPU or other PCIe devices
* **DMA Operations**: Models Direct Memory Access transfers
* **Protocol Overhead**: Accounts for protocol headers and software stack latency
* **Switch Latency**: Models network switch and routing delays
* **Host Interface Controller**: Simulates NIC and HBA processing times
* **Software Drivers**: Models driver stack latency in data paths

Using Network Components
------------------------

Adding a network transfer component to your AO pipeline is straightforward:

.. code-block:: python

    from daolite import Pipeline, PipelineComponent, ComponentType
    from daolite.utils.network import TimeOnNetwork
    from daolite.compute import hardware
    
    # Create a pipeline
    pipeline = Pipeline()
    
    # Define a CPU resource for network operations
    cpu = hardware.amd_epyc_7763()
    
    # Add components before network transfer...
    # ...
    
    # Add network transfer component
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.NETWORK,
        name="Slope Data Transfer",
        compute=cpu,
        function=TimeOnNetwork,
        params={
            "data_size": 12800 * 4,  # Bytes to transfer (12800 slopes, 4 bytes each)
            "network_speed": 100e9,  # 100 Gbps network
        },
        dependencies=["Centroider"]
    ))

Network Configuration
---------------------

Network components accept various parameters to customize their behavior:

.. code-block:: python

    params={
        # Required parameters
        "data_size": 51200,  # Bytes to transfer
        
        # Optional parameters
        "network_speed": 100e9,  # Network speed in bits/second
        "protocol": "tcp",  # "tcp", "udp", "roce", "infiniband"
        "mtu": 9000,  # Maximum Transmission Unit in bytes
        "packet_overhead": 40,  # Protocol overhead bytes per packet
        "switch_latency": 0.5,  # Switch latency in microseconds
        "distance": 5,  # Cable distance in meters
        "propagation_speed": 0.7,  # Speed of light factor in medium
        "time_in_driver": 5,  # Time spent in software driver (μs)
        "use_zero_copy": False,  # Use zero-copy transfer
        "num_connections": 1,  # Number of parallel connections
    }

Available Transfer Models
-------------------------

DaoLITE provides timing models for the following data transfer methods:

Ethernet Transfer
~~~~~~~~~~~~~~~~~

Models data transfer over standard Ethernet networks:

.. code-block:: python

    from daolite.utils.network import TimeOnNetwork
    
    # Use as a standalone function
    timing = TimeOnNetwork(
        compute=cpu,
        data_size=51200,  # 50 KB
        network_speed=100e9,  # 100 Gbps
    )
    
    # Or in a pipeline component
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.NETWORK,
        name="Ethernet Transfer",
        compute=cpu,
        function=TimeOnNetwork,
        params={
            "data_size": 51200,
            "network_speed": 100e9,
        },
        dependencies=["Previous Component"]
    ))

InfiniBand Transfer
~~~~~~~~~~~~~~~~~~~

Models high-performance InfiniBand data transfer:

.. code-block:: python

    from daolite.utils.network import TimeOnNetwork
    
    # Add as a pipeline component
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.NETWORK,
        name="InfiniBand Transfer",
        compute=cpu,
        function=TimeOnNetwork,
        params={
            "data_size": 51200,
            "network_speed": 200e9,  # 200 Gbps HDR InfiniBand
        },
        dependencies=["Previous Component"]
    ))

PCIe Transfer
~~~~~~~~~~~~~

Models data transfer over PCI Express buses:

.. code-block:: python

    from daolite.pipeline.network import pcie_transfer
    
    # Add as a pipeline component
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.TRANSFER,
        name="PCIe Transfer",
        compute=cpu,
        function=pcie_transfer,
        params={
            "data_size": 51200,
            "pcie_gen": 4,  # PCIe Generation (3, 4, 5)
            "pcie_lanes": 16,  # Number of PCIe lanes
            "direction": "h2d",  # Host to device
            "use_dma": True,  # Use DMA
            "driver_overhead": 2  # μs
        },
        dependencies=["Previous Component"]
    ))

RoCE Transfer
~~~~~~~~~~~~~

Models RDMA over Converged Ethernet:

.. code-block:: python

    from daolite.utils.network import TimeOnNetwork
    
    # Add as a pipeline component
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.NETWORK,
        name="RoCE Transfer",
        compute=cpu,
        function=TimeOnNetwork,
        params={
            "data_size": 51200,
            "network_speed": 100e9,  # 100 Gbps
        },
        dependencies=["Previous Component"]
    ))

Shared Memory Transfer
~~~~~~~~~~~~~~~~~~~~~~

Models high-speed data transfer within a node using shared memory:

.. code-block:: python

    from daolite.pipeline.network import shared_memory_transfer
    
    # Add as a pipeline component
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.TRANSFER,
        name="Shared Memory Transfer",
        compute=cpu,
        function=shared_memory_transfer,
        params={
            "data_size": 51200,
            "memory_type": "numa_local",  # "numa_local", "numa_remote", "smp"
            "cache_behavior": "cache_friendly",  # Cache behavior
            "use_hugepages": True  # Use huge pages
        },
        dependencies=["Previous Component"]
    ))

Performance Considerations
--------------------------

The latency and throughput of network and transfer operations depends on several factors:

* **Data Size**: Larger transfers have higher latency but better throughput efficiency
* **Network Technology**: Different technologies offer different latency and bandwidth
* **Protocol**: Protocol choice impacts overhead and latency
* **MTU Size**: Larger MTUs reduce protocol overhead but increase single-packet latency
* **Distance**: Longer distances increase propagation delay
* **Switch Count**: More network hops add latency
* **Driver Stack**: Software processing adds variable latency
* **Memory Operations**: Memory copies can significantly impact performance

Modeling Network Protocol Effects
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

DaoLITE accurately models how different protocols affect transfer performance:

.. code-block:: python

    # Compare protocol effects
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.NETWORK,
        name="TCP Transfer",
        compute=cpu,
        function=TimeOnNetwork,
        params={
            "data_size": 51200,
            "network_speed": 100e9,
        },
        dependencies=["Previous Component"]
    ))
    
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.NETWORK,
        name="UDP Transfer",
        compute=cpu,
        function=TimeOnNetwork,
        params={
            "data_size": 51200,
            "network_speed": 100e9,
        },
        dependencies=["Previous Component"]
    ))
    
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.NETWORK,
        name="RDMA Transfer",
        compute=cpu,
        function=TimeOnNetwork,
        params={
            "data_size": 51200,
            "network_speed": 100e9,
        },
        dependencies=["Previous Component"]
    ))

Scaling with Data Size
~~~~~~~~~~~~~~~~~~~~~~

DaoLITE models how transfer performance scales with different data sizes:

.. code-block:: python

    # Small transfer (control commands)
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.NETWORK,
        name="Small Transfer",
        compute=cpu,
        function=TimeOnNetwork,
        params={
            "data_size": 1024,  # 1 KB
            "network_speed": 100e9,
        },
        dependencies=["Previous Component"]
    ))
    
    # Medium transfer (slope data)
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.NETWORK,
        name="Medium Transfer",
        compute=cpu,
        function=TimeOnNetwork,
        params={
            "data_size": 100*1024,  # 100 KB
            "network_speed": 100e9,
        },
        dependencies=["Previous Component"]
    ))
    
    # Large transfer (pixel data)
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.NETWORK,
        name="Large Transfer",
        compute=cpu,
        function=TimeOnNetwork,
        params={
            "data_size": 4*1024*1024,  # 4 MB
            "network_speed": 100e9,
        },
        dependencies=["Previous Component"]
    ))

Customizing Network Models
--------------------------

DaoLITE allows you to create custom network transfer models with your own timing characteristics:

.. code-block:: python

    def custom_network_model(compute, data_size, network_speed=100e9, extra_param=1.0, debug=False):
        """
        Custom network transfer timing model.
        
        Args:
            compute: Compute resource
            data_size: Bytes to transfer
            network_speed: Network speed in bits/second
            extra_param: Custom scaling parameter
            debug: Enable debug output
            
        Returns:
            Numpy array with timing information
        """
        # Calculate basic transfer time (bytes * 8 bits/byte / bits/second)
        bits_to_transfer = data_size * 8
        wire_time = bits_to_transfer / network_speed * 1e6  # μs
        
        # Protocol overhead (e.g., 10%)
        protocol_overhead = 0.1
        protocol_time = wire_time * protocol_overhead
        
        # Software stack time (fixed component + variable component)
        fixed_driver_time = 5.0  # μs
        variable_driver_time = data_size * 0.0001  # 0.0001 μs per byte
        
        # Switch and propagation time
        switch_time = 0.5  # μs
        propagation_time = 0.1  # μs
        
        # Total transfer time
        transfer_time = (wire_time + protocol_time + fixed_driver_time + 
                        variable_driver_time + switch_time + propagation_time)
        
        # Apply custom scaling
        transfer_time *= extra_param
        
        if debug:
            print(f"Data size: {data_size} bytes")
            print(f"Wire time: {wire_time:.2f} μs")
            print(f"Protocol overhead: {protocol_time:.2f} μs")
            print(f"Driver time: {fixed_driver_time + variable_driver_time:.2f} μs")
            print(f"Switch and propagation: {switch_time + propagation_time:.2f} μs")
            print(f"Total transfer time: {transfer_time:.2f} μs")
        
        # Create timing array - single entry for simple transfer
        timing = np.zeros([1, 2])
        timing[0, 1] = transfer_time
        
        return timing
    
    # Use custom network model in a pipeline
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.NETWORK,
        name="Custom Network Transfer",
        compute=cpu,
        function=custom_network_model,
        params={
            "data_size": 51200,
            "network_speed": 100e9,
            "extra_param": 1.2,
            "debug": True
        },
        dependencies=["Previous Component"]
    ))

Optimizing Data Transfers
-------------------------

DaoLITE models various optimization techniques for data transfers:

Zero-Copy Transfers
~~~~~~~~~~~~~~~~~~~

Eliminating memory copies for better performance:

.. code-block:: python

    from daolite.utils.network import TimeOnNetwork
    
    # Add optimized transfer to the pipeline
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.NETWORK,
        name="Zero-Copy Transfer",
        compute=cpu,
        function=TimeOnNetwork,
        params={
            "data_size": 4*1024*1024,  # 4 MB
            "network_speed": 100e9,
        },
        dependencies=["Previous Component"]
    ))

Parallel Transfers
~~~~~~~~~~~~~~~~~~

Using multiple connections for higher throughput:

.. code-block:: python

    from daolite.pipeline.network import parallel_transfer
    
    # Add parallel transfer to the pipeline
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.NETWORK,
        name="Parallel Transfer",
        compute=cpu,
        function=parallel_transfer,
        params={
            "data_size": 100*1024*1024,  # 100 MB
            "network_speed": 100e9,
            "protocol": "tcp",
            "num_connections": 8,  # Use 8 parallel connections
            "connection_overhead": 2  # μs overhead per connection
        },
        dependencies=["Previous Component"]
    ))

Data Compression
~~~~~~~~~~~~~~~~

Using compression to reduce transfer size:

.. code-block:: python

    from daolite.pipeline.network import compressed_transfer
    
    # Add compressed transfer to the pipeline
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.NETWORK,
        name="Compressed Transfer",
        compute=cpu,
        function=compressed_transfer,
        params={
            "data_size": 10*1024*1024,  # 10 MB
            "network_speed": 100e9,
            "protocol": "tcp",
            "compression_ratio": 0.5,  # 50% compression
            "compression_time": 100,  # μs to compress
            "decompression_time": 80  # μs to decompress
        },
        dependencies=["Previous Component"]
    ))

Real-World Applications
-----------------------

Example: Low-Latency AO Control Network
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Network configuration for a low-latency AO control system:

.. code-block:: python

    # Low-latency control network
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.NETWORK,
        name="AO Control Network",
        compute=cpu,
        function=TimeOnNetwork,
        params={
            "data_size": 5000*4,  # 5000 actuators, 4 bytes each
            "network_speed": 100e9,  # 100 Gbps
        },
        dependencies=["DM Controller"]
    ))

Example: High-Bandwidth Pixel Transfer
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Network configuration for transferring large pixel arrays from camera to processing system:

.. code-block:: python

    # High-bandwidth pixel transfer
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.NETWORK,
        name="Pixel Data Transfer",
        compute=cpu,
        function=TimeOnNetwork,
        params={
            "data_size": 2048*2048*2,  # 2K x 2K sensor, 2 bytes per pixel
            "network_speed": 200e9,  # 200 Gbps HDR InfiniBand
        },
        dependencies=["WFS Camera"]
    ))

Example: GPU Data Transfer
~~~~~~~~~~~~~~~~~~~~~~~~~~

Configuration for transferring data between CPU and GPU:

.. code-block:: python

    # Host to GPU transfer
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.TRANSFER,
        name="Host to GPU Transfer",
        compute=cpu,
        function=pcie_transfer,
        params={
            "data_size": 1024*1024*4,  # 4 MB of pixel data
            "pcie_gen": 4,  # PCIe Gen 4
            "pcie_lanes": 16,  # x16 interface
            "direction": "h2d",  # Host to device
            "use_dma": True,  # Use DMA
            "use_pinned_memory": True  # Use pinned memory for faster transfers
        },
        dependencies=["Pixel Calibration"]
    ))
    
    # GPU to host transfer
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.TRANSFER,
        name="GPU to Host Transfer",
        compute=gpu,
        function=pcie_transfer,
        params={
            "data_size": 5000*4,  # 5000 actuators, 4 bytes each
            "pcie_gen": 4,  # PCIe Gen 4
            "pcie_lanes": 16,  # x16 interface
            "direction": "d2h",  # Device to host
            "use_dma": True,  # Use DMA
            "use_pinned_memory": True  # Use pinned memory for faster transfers
        },
        dependencies=["Reconstructor"]
    ))

API Reference
-------------

For complete API details, see the :ref:`api_network` section.