from dataclasses import dataclass
import yaml
import regex as re

@dataclass
class ComputeResources:
    # ...existing fields and methods from compute_resources.py...
    hardware: str = "CPU"
    memory_bandwidth: float = 32e9 * 8  # 32 GB/s (converted to bits/s internally)
    flops: float = 2.4e9  # 2.4 GFLOPS
    network_speed: float = 10e9  # 10 Gbps
    time_in_driver: float = 5.0  # microseconds
    core_fudge: float = 0.8
    mem_fudge: float = 1.0
    network_fudge: float = 0.8
    adjust: float = 1e6  # Convert to microseconds
    cores: int = 16
    core_frequency: float = 2.6e9
    flops_per_cycle: float = 32
    memory_frequency: float = 3200e6
    memory_width: int = 64
    memory_channels: int = 4

    def get_memory_bandwidth(self) -> float:
        """
        Returns memory bandwidth in bits/sec (internal unit).
        """
        return self.memory_bandwidth * self.mem_fudge

    def get_flops(self) -> float:
        return self.flops * self.core_fudge

    def load_time(self, memory_size) -> float:
        """
        memory_size: in bits
        memory_bandwidth: in bits/sec
        Returns time in microseconds.
        """
        return (memory_size / self.get_memory_bandwidth()) * self.adjust

    def network_time(self, data_size) -> float:
        return (
            data_size * 8 / (self.network_speed * self.network_fudge)
        ) * self.adjust + self.time_in_driver

    def calc_time(self, n_flops) -> float:
        return (n_flops / self.get_flops()) * self.adjust

    def total_time(self, memory_size, n_flops) -> float:
        return self.calc_time(n_flops) + self.load_time(memory_size)

    def to_dict(self):
        """Serialize compute resource to a dictionary."""
        return self.__dict__

    @staticmethod
    def from_dict(data):
        """Deserialize compute resource from a dictionary."""
        return ComputeResources(**data)

def create_compute_resources(
    cores,
    core_frequency,
    flops_per_cycle,
    memory_frequency,
    memory_width,
    memory_channels,
    network_speed,
    time_in_driver,
    hardware="CPU",
    **kwargs,
):
    # Manufacturer spec is bytes/sec, convert to bits/sec for internal use
    memory_bandwidth_bytes = memory_frequency * memory_width * memory_channels / 8
    memory_bandwidth_bits = memory_bandwidth_bytes * 8
    flops = cores * core_frequency * flops_per_cycle
    return ComputeResources(
        hardware=hardware,
        memory_bandwidth=memory_bandwidth_bits,  # store as bits/sec
        flops=flops,
        network_speed=network_speed,
        time_in_driver=time_in_driver,
        cores=cores,
        core_frequency=core_frequency,
        flops_per_cycle=flops_per_cycle,
        memory_frequency=memory_frequency,
        memory_width=memory_width,
        memory_channels=memory_channels,
        **kwargs,
    )

def create_gpu_resource(
    flops, memory_bandwidth, network_speed=100e9, time_in_driver=8.0, **kwargs
):
    # Assume memory_bandwidth is given in bytes/sec, convert to bits/sec
    memory_bandwidth_bits = memory_bandwidth * 8
    return ComputeResources(
        hardware="GPU",
        memory_bandwidth=memory_bandwidth_bits,
        flops=flops,
        network_speed=network_speed,
        time_in_driver=time_in_driver,
        **kwargs,
    )

def create_compute_resources_from_yaml(yaml_file):
    loader = yaml.SafeLoader
    loader.add_implicit_resolver(
    u'tag:yaml.org,2002:float',
    re.compile(u'''^(?:
     [-+]?(?:[0-9][0-9_]*)\\.[0-9_]*(?:[eE][-+]?[0-9]+)?
    |[-+]?(?:[0-9][0-9_]*)(?:[eE][-+]?[0-9]+)
    |\\.[0-9_]+(?:[eE][-+][0-9]+)?
    |[-+]?[0-9][0-9_]*(?::[0-5]?[0-9])+\\.[0-9_]*
    |[-+]?\\.(?:inf|Inf|INF)
    |\\.(?:nan|NaN|NAN))$''', re.X),
    list(u'-+0123456789.'))

    with open(yaml_file, "r") as file:
        data = yaml.safe_load(file)
    hardware_type = data.get("hardware", "CPU")
    if hardware_type == "CPU":
        return create_compute_resources(
            cores=data["cores"],
            core_frequency=data["core_frequency"],
            flops_per_cycle=data["flops_per_cycle"],
            memory_frequency=data["memory_frequency"],
            memory_width=data["memory_width"],
            memory_channels=data["memory_channels"],
            network_speed=data["network_speed"],
            time_in_driver=data["time_in_driver"],
        )
    elif hardware_type == "GPU":
        flops = data.get("flops")
        if flops is None:
            flops = data.get("fp32_tflops")
            if flops is None:
                raise ValueError(
                    "Either 'flops' or 'fp32_tflops' must be provided for GPU configurations"
                )
        return create_gpu_resource(
            flops=flops,
            memory_bandwidth=data["memory_bandwidth"],
            network_speed=data["network_speed"],
            time_in_driver=data["time_in_driver"],
        )
    else:
        # For invalid hardware types, return None (do not raise)
        return None

def create_compute_resources_from_system():
    """
    Create a ComputeResources instance by scanning the current system hardware.
    Works on Windows, macOS, and Linux systems.

    Returns:
        ComputeResources: Configured compute resource object based on current hardware
    """
    import platform
    import subprocess
    import shutil
    import re
    import psutil
    import os

    system = platform.system()

    # Default values - will be updated based on detected hardware
    cores = 1
    core_frequency = 2.0e9  # 2 GHz
    flops_per_cycle = 8.0  # Conservative estimate for modern CPUs
    memory_frequency = 2.4e9  # 2400 MHz (DDR4)
    memory_width = 64  # 64-bit
    memory_channels = 2  # Dual channel
    network_speed = 1e9  # 1 Gbps default
    time_in_driver = 5.0  # microseconds

    # Get CPU information (cross-platform)
    try:
        # Get CPU core count
        cores = psutil.cpu_count(logical=False)
        if cores is None:  # If physical count unavailable
            cores = psutil.cpu_count(logical=True)
            if cores is None:  # Fallback
                cores = 1

        # Get CPU frequency
        cpu_freq = psutil.cpu_freq()
        if cpu_freq and cpu_freq.max:
            core_frequency = cpu_freq.max * 1e6  # Convert MHz to Hz

        # Estimate FLOPS per cycle based on architecture
        # Modern x86-64 CPUs can do 16-32 FLOPs per cycle with AVX2/AVX-512
        # ARM CPUs typically can do 8-16 FLOPs per cycle with NEON
        # Use a conservative estimate by default
        if platform.machine() in ("x86_64", "AMD64"):
            flops_per_cycle = 16.0
        elif platform.machine() in ("arm64", "aarch64"):
            flops_per_cycle = 8.0

    except Exception as e:
        print(f"Error getting CPU info: {e}")

    # Get memory information (cross-platform)
    try:
        # Get total RAM
        psutil.virtual_memory().total

        # Estimate memory specs based on platform
        if system == "Windows":
            try:
                # Try using wmic on Windows
                output = subprocess.check_output(
                    "wmic memorychip get speed", shell=True
                ).decode()
                speeds = re.findall(r"\d+", output)
                if speeds:
                    memory_frequency = float(speeds[0]) * 1e6  # MHz to Hz

                # Check memory channels (estimate based on physical memory sticks)
                output = subprocess.check_output(
                    "wmic memorychip get devicelocator", shell=True
                ).decode()
                channels = len(
                    [
                        line
                        for line in output.split("\n")
                        if line.strip() and "devicelocator" not in line.lower()
                    ]
                )
                if channels > 0:
                    memory_channels = channels
            except:
                pass

        elif system == "Darwin":  # macOS
            try:
                output = subprocess.check_output(
                    ["system_profiler", "SPMemoryDataType"], text=True
                )
                if "MHz" in output:
                    match = re.search(r"(\d+) MHz", output)
                    if match:
                        memory_frequency = float(match.group(1)) * 1e6  # MHz to Hz

                # Count memory slots
                channels = output.count("BANK")
                if channels > 0:
                    memory_channels = channels
            except:
                pass

        elif system == "Linux":
            try:
                # Try to get memory frequency from Linux
                if os.path.exists("/proc/cpuinfo"):
                    with open("/proc/cpuinfo", "r") as f:
                        f.read()

                # Try to get memory info from dmidecode
                if shutil.which("dmidecode"):
                    output = subprocess.check_output(
                        ["sudo", "dmidecode", "-t", "memory"], text=True
                    )
                    if "MT/s" in output or "MHz" in output:
                        match = re.search(r"(\d+) MT/s|(\d+) MHz", output)
                        if match:
                            speed = match.group(1) or match.group(2)
                            memory_frequency = float(speed) * 1e6  # MHz to Hz

                    # Estimate channels from number of populated slots
                    channels = len(re.findall("Size:.+?MB|Size:.+?GB", output))
                    if channels > 0:
                        memory_channels = channels
            except:
                pass

    except Exception as e:
        print(f"Error getting memory info: {e}")

    # Get network speed (cross-platform)
    try:
        # Get the active network interfaces
        network_stats = psutil.net_if_stats()
        max_speed = 0

        for interface, stats in network_stats.items():
            if stats.isup and hasattr(stats, "speed") and stats.speed > 0:
                speed = stats.speed * 1e6  # Convert Mbps to bps
                max_speed = max(max_speed, speed)

        if max_speed > 0:
            network_speed = max_speed
    except Exception as e:
        print(f"Error getting network info: {e}")

    # Check for GPU
    has_gpu = False
    gpu_flops = 0
    gpu_memory_bandwidth = 0

    # Check for NVIDIA GPU with nvidia-smi
    if shutil.which("nvidia-smi"):
        try:
            output = subprocess.check_output(
                [
                    "nvidia-smi",
                    "--query-gpu=name,memory.total,memory.clock,memory.width",
                    "--format=csv,noheader,nounits",
                ],
                text=True,
            )
            if output.strip():
                has_gpu = True
                parts = output.strip().split(",")

                # Roughly estimate GPU performance based on model
                # This is a very rough estimate - ideally we'd use a database of GPU specs
                gpu_name = parts[0].strip().lower()

                # Memory bandwidth calculation if available
                if len(parts) >= 4:
                    try:
                        mem_clock = float(parts[2].strip()) * 1e6  # MHz to Hz
                        mem_width = float(parts[3].strip())
                        # Memory bandwidth = clock * width * 2 (DDR) / 8 (bits to bytes)
                        gpu_memory_bandwidth = mem_clock * mem_width * 2 / 8
                    except:
                        # Default value for modern GPUs
                        gpu_memory_bandwidth = 300e9  # 300 GB/s

                # Rough estimate of FLOPS based on common NVIDIA GPUs
                if "rtx 3090" in gpu_name:
                    gpu_flops = 35.6e12  # 35.6 TFLOPS
                elif "rtx 3080" in gpu_name:
                    gpu_flops = 29.8e12  # 29.8 TFLOPS
                elif "rtx 3070" in gpu_name:
                    gpu_flops = 20.3e12  # 20.3 TFLOPS
                elif "rtx 2080" in gpu_name:
                    gpu_flops = 10.1e12  # 10.1 TFLOPS
                elif "gtx 1080" in gpu_name:
                    gpu_flops = 8.9e12  # 8.9 TFLOPS
                elif "rtx" in gpu_name:
                    gpu_flops = 15.0e12  # Generic RTX estimate
                elif "gtx" in gpu_name:
                    gpu_flops = 7.0e12  # Generic GTX estimate
                else:
                    gpu_flops = 5.0e12  # Generic NVIDIA GPU estimate
        except Exception as e:
            print(f"Error getting NVIDIA GPU info: {e}")

    # Check for AMD GPU on Linux
    elif system == "Linux" and shutil.which("rocminfo"):
        try:
            output = subprocess.check_output(["rocminfo"], text=True)
            if "GPU" in output:
                has_gpu = True
                # Default values for modern AMD GPUs
                gpu_memory_bandwidth = 300e9  # 300 GB/s
                gpu_flops = 10.0e12  # 10 TFLOPS
        except Exception as e:
            print(f"Error getting AMD GPU info: {e}")

    # Check for AMD GPU on Windows
    elif system == "Windows" and shutil.which("wmic"):
        try:
            output = subprocess.check_output(
                "wmic path win32_VideoController get name", shell=True
            ).decode()
            if "Radeon" in output or "AMD" in output:
                has_gpu = True
                # Default values for modern AMD GPUs
                gpu_memory_bandwidth = 300e9  # 300 GB/s
                gpu_flops = 10.0e12  # 10 TFLOPS
        except Exception as e:
            print(f"Error getting AMD GPU info: {e}")

    # Check for GPU on macOS
    elif system == "Darwin":
        try:
            output = subprocess.check_output(
                ["system_profiler", "SPDisplaysDataType"], text=True
            )
            if "Metal" in output:
                has_gpu = True
                # Apple GPUs - use conservative estimates
                gpu_memory_bandwidth = 200e9  # 200 GB/s
                gpu_flops = 5.0e12  # 5 TFLOPS
        except Exception as e:
            print(f"Error getting macOS GPU info: {e}")

    # Create appropriate resource object
    if has_gpu and gpu_flops > 0:
        # Create GPU resource
        return create_gpu_resource(
            flops=gpu_flops,
            memory_bandwidth=gpu_memory_bandwidth,
            network_speed=network_speed,
            time_in_driver=10.0,  # GPU typically has higher driver overhead
        )
    else:
        # Create CPU resource
        return create_compute_resources(
            cores=cores,
            core_frequency=core_frequency,
            flops_per_cycle=flops_per_cycle,
            memory_frequency=memory_frequency,
            memory_width=memory_width,
            memory_channels=memory_channels,
            network_speed=network_speed,
            time_in_driver=time_in_driver,
        )