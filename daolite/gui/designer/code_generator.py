"""
Code generator for the daolite pipeline designer.

This module generates executable Python code from a visual pipeline design.
"""

from typing import List

from daolite.common import ComponentType
from .components import ComponentBlock
from daolite.compute import create_compute_resources


class CodeGenerator:
    """
    Generates executable Python code from pipeline design.

    This class analyzes the component blocks and connections in a
    pipeline design and produces executable code that creates the
    equivalent daolite pipeline.
    """

    def __init__(self, components: List[ComponentBlock]):
        """
        Initialize with a list of component blocks.

        Args:
            components: List of component blocks in the pipeline
        """
        self.components = components
        self.import_statements = set(
            [
                "import numpy as np",
                "from daolite import Pipeline, PipelineComponent, ComponentType",
            ]
        )

    def generate_code(self) -> str:
        """
        Generate executable Python code for the pipeline.

        Returns:
            str: Python code that creates the designed pipeline
        """
        code_parts = []

        # Generate import statements
        self._add_required_imports()
        imports = "\n".join(sorted(self.import_statements))
        code_parts.append(imports)
        code_parts.append("")  # Empty line

        # Generate pipeline creation
        code_parts.append("# Create a pipeline")
        code_parts.append("pipeline = Pipeline()")
        code_parts.append("")  # Empty line

        # Generate component code in dependency order
        ordered_components = self._sort_components_by_dependencies()
        for component in ordered_components:
            code_parts.append(self._generate_component_code(component))
            code_parts.append("")  # Empty line

        # Generate code to run the pipeline
        code_parts.append("# Run the pipeline")
        code_parts.append("timing_results = pipeline.run(debug=True)")
        code_parts.append("")

        # Generate visualization code
        code_parts.append("# Visualize the pipeline timing")
        code_parts.append("pipeline.visualize(")
        code_parts.append('    title="AO Pipeline Timing",')
        code_parts.append('    save_path="ao_pipeline_timing.png"')
        code_parts.append(")")

        return "\n".join(code_parts)

    def _add_required_imports(self):
        """Add required import statements based on component types."""
        # Add imports for compute resources
        self.import_statements.add(
            "from daolite.compute import create_compute_resources"
        )

        # Track which camera functions are used
        used_camera_funcs = set()
        for component in self.components:
            if component.component_type == ComponentType.CAMERA:
                camera_func = component.params.get("camera_function", "PCOCamLink")
                used_camera_funcs.add(camera_func)
        if used_camera_funcs:
            cam_imports = ", ".join(sorted(used_camera_funcs))
            self.import_statements.add(
                f"from daolite.simulation.camera import {cam_imports}"
            )

        # Remove any import of simulate_camera_readout
        self.import_statements = {
            imp
            for imp in self.import_statements
            if "simulate_camera_readout" not in imp
        }

        # Check for component types and add relevant imports
        has_network = False
        for component in self.components:
            # Add component-specific imports
            if component.component_type == ComponentType.CENTROIDER:
                self.import_statements.add(
                    "from daolite.pipeline.centroider import Centroider, cross_correlation_centroider"
                )

            elif component.component_type == ComponentType.RECONSTRUCTION:
                self.import_statements.add(
                    "from daolite.pipeline.reconstruction import Reconstruction, mvr_reconstruction"
                )

            elif component.component_type == ComponentType.CONTROL:
                self.import_statements.add(
                    "from daolite.pipeline.control import FullFrameControl, dm_control"
                )

            elif component.component_type == ComponentType.CALIBRATION:
                self.import_statements.add(
                    "from daolite.pipeline.calibration import PixelCalibration"
                )

            elif component.component_type == ComponentType.NETWORK:
                has_network = True

            # Check for compute resources
            if component.compute:
                compute_class = component.compute.__class__.__name__
                if "nvidia" in compute_class.lower() or "amd" in compute_class.lower():
                    for resource_name in [
                        "amd_epyc_7763",
                        "amd_epyc_9654",
                        "nvidia_a100_80gb",
                        "nvidia_h100_80gb",
                        "nvidia_rtx_4090",
                    ]:
                        if resource_name in compute_class.lower():
                            self.import_statements.add(
                                f"from daolite import {resource_name}"
                            )

        # For visualization
        self.import_statements.add("import matplotlib.pyplot as plt")

        # Only import network_transfer if it exists in network.py
        if has_network:
            try:
                import os

                network_path = os.path.join(
                    os.path.dirname(__file__), "../../utils/network.py"
                )
                with open(network_path, "r") as f:
                    network_code = f.read()
                if "network_transfer" in network_code:
                    self.import_statements.add(
                        "from daolite.utils.network import network_transfer"
                    )
                if "TimeOnNetwork" in network_code:
                    self.import_statements.add(
                        "from daolite.utils.network import TimeOnNetwork"
                    )
            except Exception:
                pass

    def _generate_component_code(self, component: ComponentBlock) -> str:
        """
        Generate code for a specific component.

        Args:
            component: Component block to generate code for

        Returns:
            str: Python code for adding this component to the pipeline
        """
        lines = []

        # Add comment
        lines.append(
            f"# Add {component.name} component ({component.component_type.value})"
        )

        # Add component creation code
        lines.append(f"pipeline.add_component(PipelineComponent(")
        lines.append(
            f"    component_type=ComponentType.{component.component_type.name},"
        )
        lines.append(f'    name="{component.name}",')

        # Add compute resource
        if component.compute:
            # Try to get a readable name for the compute resource
            compute_code = self._get_compute_resource_code(component)
            lines.append(f"    compute={compute_code},")
        else:
            # Use default values for all required arguments
            lines.append(
                "    compute=create_compute_resources("
                "cores=16, core_frequency=2.6e9, flops_per_cycle=32, "
                "memory_frequency=3.2e9, memory_width=64, memory_channels=8, "
                "network_speed=100e9, time_in_driver=5.0),"
            )

        # Add function name based on component type
        function_name = self._get_function_name_for_component(component)
        # Camera: use selected camera simulation function
        if component.component_type == ComponentType.CAMERA:
            # Use a parameter or default to PCOCamLink
            camera_func = component.params.get("camera_function", "PCOCamLink")
            lines.append(f"    function={camera_func},")
        else:
            lines.append(f"    function={function_name},")

        # Add parameters
        param_lines = self._generate_params_code(component)
        # Insert params block with a trailing comma
        if param_lines:
            # Remove the last '}'
            if param_lines[-1].strip() == "}":
                param_lines[-1] = "},"
            lines.extend([f"    {param_line}" for param_line in param_lines])

        # Add dependencies
        dependencies = component.get_dependencies()
        if dependencies:
            deps_str = ", ".join([f'"{dep}"' for dep in dependencies])
            lines.append(f"    dependencies=[{deps_str}]")
        else:
            lines.append(f"    dependencies=[]  # No dependencies")

        # Close the function call
        lines.append("))")

        return "\n".join(lines)

    def _get_function_name_for_component(self, component: ComponentBlock) -> str:
        """Get the appropriate function name based on component type."""
        if component.component_type == ComponentType.CAMERA:
            return "simulate_camera_readout"
        elif component.component_type == ComponentType.CENTROIDER:
            return "cross_correlation_centroider"
        elif component.component_type == ComponentType.RECONSTRUCTION:
            return "mvr_reconstruction"
        elif component.component_type == ComponentType.CONTROL:
            return "dm_control"
        elif component.component_type == ComponentType.CALIBRATION:
            return "PixelCalibration"
        elif component.component_type == ComponentType.NETWORK:
            return "TimeOnNetwork"  # Use TimeOnNetwork for network components
        else:
            return "unknown_function"  # Default

    def _get_compute_resource_code(self, component: ComponentBlock) -> str:
        # Always provide all required arguments for create_compute_resources
        if component.compute:
            # If the component has a compute object, try to extract values
            c = component.compute
            return (
                f"create_compute_resources("
                f"cores={getattr(c, 'cores', 16)}, "
                f"core_frequency={getattr(c, 'core_frequency', 2.6e9)}, "
                f"flops_per_cycle={getattr(c, 'flops_per_cycle', 32)}, "
                f"memory_frequency={getattr(c, 'memory_frequency', 3.2e9)}, "
                f"memory_width={getattr(c, 'memory_width', 64)}, "
                f"memory_channels={getattr(c, 'memory_channels', 8)}, "
                f"network_speed={getattr(c, 'network_speed', 100e9)}, "
                f"time_in_driver={getattr(c, 'time_in_driver', 5.0)})"
            )
        else:
            # Use default values
            return (
                "create_compute_resources("
                "cores=16, core_frequency=2.6e9, flops_per_cycle=32, "
                "memory_frequency=3.2e9, memory_width=64, memory_channels=8, "
                "network_speed=100e9, time_in_driver=5.0)"
            )

    def _generate_params_code(self, component: ComponentBlock) -> List[str]:
        lines = []
        lines.append("params={")
        # Add default parameters based on component type
        if component.component_type == ComponentType.CAMERA:
            camera_func = component.params.get("camera_function", "PCOCamLink")
            if camera_func == "PCOCamLink":
                lines.append('    "n_pixels": 1024 * 1024,  # 1MP camera')
                lines.append(
                    '    "group": 50,  # Default packet count (was group_size)'
                )
            elif (
                camera_func == "GigeVisionCamera"
                or camera_func == "RollingShutterCamera"
            ):
                lines.append('    "n_pixels": 1024 * 1024,  # 1MP camera')
                lines.append(
                    '    "group": 50,  # Default packet count (was group_size)'
                )
            # Add more camera types here as needed
        elif component.component_type == ComponentType.CENTROIDER:
            lines.append('    "n_subaps": 5120,  # Valid subapertures (80x80 * 0.8)')
            lines.append('    "pixels_per_subap": 256  # 16x16 pixels per subaperture')
        elif component.component_type == ComponentType.RECONSTRUCTION:
            lines.append('    "n_slopes": 5120 * 2,  # X and Y slopes')
            lines.append('    "n_actuators": 5000  # DM actuators')
        elif component.component_type == ComponentType.CONTROL:
            lines.append('    "n_actuators": 5000  # DM actuators')
        elif component.component_type == ComponentType.CALIBRATION:
            lines.append('    "n_pixels": 1024 * 1024,  # 1MP camera')
            lines.append('    "group": 50  # Default packet count')
        elif component.component_type == ComponentType.NETWORK:
            lines.append('    "n_bits": 5000 * 32,  # 32 bits per actuator')
        # Add custom parameters from component
        for key, value in component.params.items():
            # Map group_size to group for camera functions
            if component.component_type == ComponentType.CAMERA and key == "group_size":
                key = "group"
            if isinstance(value, str):
                lines.append(f'    "{key}": "{value}",')
            else:
                lines.append(f'    "{key}": {value},')
        lines.append("}")
        return lines

    def _sort_components_by_dependencies(self) -> List[ComponentBlock]:
        """
        Sort components in dependency order.

        Returns a list of components where all dependencies come before
        the components that depend on them.

        Returns:
            List[ComponentBlock]: Sorted components
        """
        # Create a name-to-component mapping
        comp_map = {comp.name: comp for comp in self.components}

        # Build a dependency graph
        graph = {comp.name: set(comp.get_dependencies()) for comp in self.components}

        # Find components with no dependencies
        no_deps = [name for name, deps in graph.items() if not deps]
        sorted_names = []

        # Topological sort
        while no_deps:
            name = no_deps.pop(0)
            sorted_names.append(name)

            # Find all components that depend on this one
            for dep_name, deps in list(graph.items()):
                if name in deps:
                    deps.remove(name)
                    # If no more dependencies, add to no_deps
                    if not deps and dep_name not in sorted_names:
                        no_deps.append(dep_name)

        # Check for circular dependencies
        if len(sorted_names) < len(self.components):
            # Some components couldn't be sorted
            # Add remaining components in any order
            remaining = set(comp.name for comp in self.components) - set(sorted_names)
            sorted_names.extend(remaining)

        # Convert back to component objects
        return [comp_map[name] for name in sorted_names if name in comp_map]

    def export_to_file(self, filename: str):
        """
        Export generated code to a Python file.

        Args:
            filename: Path to output file
        """
        code = self.generate_code()

        with open(filename, "w") as f:
            f.write(code)
