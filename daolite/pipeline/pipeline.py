"""
Pipeline module for flexible AO component arrangement.

This module provides classes and utilities for defining custom AO pipelines
with components in any order and on different compute resources.
"""

from typing import Dict, List, Optional, Tuple, Any
import numpy as np
from dataclasses import dataclass

from daolite.common import ComponentType
from daolite.compute import ComputeResources
from daolite.utils.chronograph import generate_chrono_plot_packetize


@dataclass
class PipelineComponent:
    """
    Definition of a single pipeline component.

    Attributes:
        component_type: Type of component (camera, centroider, etc.)
        name: User-friendly name for this component
        compute: Compute resource for this component
        function: Function to call for timing calculation
        params: Parameters to pass to the timing function
        dependencies: List of component names this component depends on
    """

    component_type: ComponentType
    name: str
    compute: ComputeResources
    function: callable
    params: Dict[str, Any]
    dependencies: List[str] = None

    def __post_init__(self):
        """Initialize dependencies as empty list if None."""
        if self.dependencies is None:
            self.dependencies = []


class Pipeline:
    """
    Flexible AO pipeline with configurable components and dependencies.

    This class allows defining components in any order on different compute
    resources, handling dependencies automatically.
    """

    def __init__(self):
        """Initialize an empty pipeline."""
        self.components: Dict[str, PipelineComponent] = {}
        self.timing_results: Dict[str, np.ndarray] = {}
        self.execution_order: List[str] = []

    def add_component(self, component: PipelineComponent) -> None:
        """
        Add a component to the pipeline.

        Args:
            component: PipelineComponent to add

        Raises:
            ValueError: If component with the same name already exists
        """
        if component.name in self.components:
            raise ValueError(f"Component {component.name} already exists in pipeline")

        self.components[component.name] = component

    def _resolve_dependencies(self) -> List[str]:
        """
        Resolve dependencies and determine execution order.

        Returns:
            List of component names in execution order

        Raises:
            ValueError: If circular dependencies are detected
        """
        # Create dependency graph
        graph = {name: set(comp.dependencies) for name, comp in self.components.items()}

        # Find components with no dependencies
        execution_order = []
        no_deps = [name for name, deps in graph.items() if not deps]

        # Topological sort
        while no_deps:
            # Add a node with no dependencies to the execution order
            node = no_deps.pop(0)
            execution_order.append(node)

            # Remove this node from the graph
            # Find nodes that depend on this one
            for name, deps in list(graph.items()):
                if node in deps:
                    deps.remove(node)
                    # If no more dependencies, add to no_deps
                    if not deps and name not in execution_order and name not in no_deps:
                        no_deps.append(name)

        # Check for circular dependencies
        if len(execution_order) != len(self.components):
            unprocessed = set(self.components.keys()) - set(execution_order)
            raise ValueError(
                f"Circular dependencies detected among components: {unprocessed}"
            )

        return execution_order

    def run(self, debug: bool = False) -> Dict[str, np.ndarray]:
        """
        Execute the pipeline and return timing results.

        Args:
            debug: Enable debug output

        Returns:
            Dict mapping component names to timing arrays

        Raises:
            ValueError: If pipeline contains circular dependencies
        """
        # Resolve dependencies and get execution order
        self.execution_order = self._resolve_dependencies()
        self.timing_results = {}

        if debug:
            print(f"\n===== Pipeline Execution Order =====")
            for i, name in enumerate(self.execution_order):
                comp = self.components[name]
                deps = ", ".join(comp.dependencies) if comp.dependencies else "none"
                print(
                    f"{i+1}. {name} ({comp.component_type.value}) - Dependencies: {deps}"
                )
            print("==================================\n")

        # Execute each component in order
        for name in self.execution_order:
            component = self.components[name]

            # Get timing results from dependencies
            dep_timings = {}
            for dep in component.dependencies:
                if dep not in self.timing_results:
                    raise ValueError(f"Dependency {dep} not yet executed")
                dep_timings[dep] = self.timing_results[dep]

            # Prepare parameters with dependency timings
            params = component.params.copy()

            # Handle start_times from dependency if needed
            if (
                "start_times" in component.function.__code__.co_varnames
                and not params.get("start_times")
            ):
                # Use the last dependency's timing as start_times
                if component.dependencies:
                    dep = component.dependencies[-1]
                    params["start_times"] = self.timing_results[dep]

            # Handle agenda-based API compatibility
            # If start_times is present and agenda is missing, create agenda from legacy params
            if params.get("start_times") is not None:
                start_times = params["start_times"]
                n_iterations = len(start_times)
                
                # Centroider: create centroid_agenda from n_valid_subaps
                if ("centroid_agenda" not in params and 
                    "_n_valid_subaps_compat" in params):
                    n_subaps = params.pop("_n_valid_subaps_compat")
                    params["centroid_agenda"] = np.ones(n_iterations, dtype=int) * n_subaps
                
                # Calibration: create pixel_agenda from n_pixels
                if ("pixel_agenda" not in params and 
                    "_n_pixels_compat" in params):
                    n_pixels = params.pop("_n_pixels_compat")
                    params["pixel_agenda"] = np.ones(n_iterations, dtype=int) * n_pixels
                
                # Reconstruction: create centroid_agenda from n_slopes
                if ("centroid_agenda" not in params and 
                    "_n_slopes_compat" in params):
                    n_slopes = params.pop("_n_slopes_compat")
                    params["centroid_agenda"] = np.ones(n_iterations, dtype=int) * n_slopes

            # Add compute_resources if needed
            if (
                "compute_resources" in component.function.__code__.co_varnames
                and not params.get("compute_resources")
            ):
                params["compute_resources"] = component.compute

            # Add debug parameter if available and requested
            if "debug" in component.function.__code__.co_varnames:
                params["debug"] = debug

            if debug:
                print(f"Executing {name} ({component.component_type.value})")

            # Execute component timing function
            timing = component.function(**params)
            self.timing_results[name] = timing

            if debug and hasattr(timing, "shape"):
                if len(timing.shape) == 2 and timing.shape[1] == 2:
                    start = timing[0, 0]
                    end = timing[-1, 1]
                    print(f"  - Duration: {end - start:.2f} μs")
                elif len(timing.shape) == 0:  # Scalar
                    print(f"  - Duration: {timing:.2f} μs")

        return self.timing_results

    def visualize(
        self,
        title: str = "AO Pipeline Timing",
        xlabel: str = "Time (μs)",
        save_path: Optional[str] = None,
    ) -> Tuple:
        """
        Visualize pipeline timing using chronograph.

        Args:
            title: Plot title
            xlabel: X-axis label
            save_path: Path to save visualization (optional)

        Returns:
            Tuple of (fig, ax, latency) from chronograph

        Raises:
            ValueError: If pipeline has not been run yet
        """
        if not self.timing_results:
            raise ValueError("Pipeline must be run before visualization")

        # Create dataset for chronograph
        data_set = []
        for name in self.execution_order:
            component = self.components[name]
            timing = self.timing_results[name]

            # Handle scalar timing results (convert to array form)
            if not isinstance(timing, np.ndarray) or len(timing.shape) == 0:
                # If previous component exists, use its end time as start
                if data_set:
                    prev_timing = data_set[-1][0]
                    start_time = (
                        prev_timing[-1, 1]
                        if len(prev_timing.shape) > 1
                        else prev_timing[1]
                    )
                else:
                    start_time = 0

                arr_timing = np.zeros([1, 2])
                arr_timing[0, 0] = start_time
                arr_timing[0, 1] = start_time + timing
                timing = arr_timing

            # Add to dataset
            data_set.append([timing, f"{name} ({component.component_type.value})"])

        # Generate chronograph visualization
        fig, ax, latency = generate_chrono_plot_packetize(
            data_list=data_set, title=title, xlabel=xlabel, multiplot=False
        )

        # Save if requested
        if save_path:
            fig.savefig(save_path, dpi=300, bbox_inches="tight")

        return fig, ax, latency
