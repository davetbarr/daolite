"""
Parameter inheritance utilities for pipeline designer.

This module provides functions to manage parameter inheritance between connected components.
"""

from typing import Dict, Any, List, Set, Tuple
from daolite.common import ComponentType


# Define parameter inheritance relationships between component types
# Format: {source_component_type: {target_component_type: [shared_parameters]}}
INHERITANCE_MAP = {
    ComponentType.CAMERA: {
        ComponentType.CENTROIDER: ["n_pixels", "n_subapertures", "pixels_per_subaperture", "bit_depth"],
        ComponentType.CALIBRATION: ["n_pixels", "bit_depth"],
        ComponentType.NETWORK: ["n_bits"],
        # All components can inherit these
        None: ["n_pixels", "bit_depth"]
    },
    ComponentType.CENTROIDER: {
        ComponentType.RECONSTRUCTION: ["n_subapertures", "n_valid_subaps"],
        ComponentType.NETWORK: ["n_bits"],
        None: ["n_subapertures", "n_valid_subaps"]
    },
    ComponentType.RECONSTRUCTION: {
        ComponentType.CONTROL: ["n_actuators", "n_modes"],
        ComponentType.NETWORK: ["n_bits"],
        None: ["n_actuators", "n_modes"]
    },
    ComponentType.CONTROL: {
        ComponentType.NETWORK: ["n_bits", "n_actuators"],
        None: ["n_actuators"]
    },
    # Network can propagate data size
    ComponentType.NETWORK: {
        ComponentType.NETWORK: ["n_bits"],
        None: ["n_bits"]
    },
    ComponentType.CALIBRATION: {
        ComponentType.CENTROIDER: ["n_pixels", "n_subapertures"],
        None: ["n_pixels"]
    }
}

# Automatic parameter mapping for propagation
# This maps parameters from one name to another when inherited (if needed)
PARAMETER_NAME_MAP = {
    "n_pixels": ["n_pixels", "image_size"],
    "n_bits": ["n_bits", "data_size"]
}


def get_inheritable_parameters(source_component, target_component) -> Dict[str, Any]:
    """
    Get parameters that can be inherited from the source component to the target component.
    
    Args:
        source_component: Source component with parameters to inherit
        target_component: Target component to inherit parameters to
        
    Returns:
        Dict of parameter name to value that can be inherited
    """
    if not hasattr(source_component, 'component_type') or not hasattr(target_component, 'component_type'):
        return {}
    
    if not hasattr(source_component, 'params') or not source_component.params:
        return {}
    
    source_type = source_component.component_type
    target_type = target_component.component_type
    
    # Find applicable parameter list for this source-target pair
    inheritable_params = set()
    
    # Check specific source->target mapping
    if source_type in INHERITANCE_MAP:
        if target_type in INHERITANCE_MAP[source_type]:
            inheritable_params.update(INHERITANCE_MAP[source_type][target_type])
        
        # Add any general parameters for this source type
        if None in INHERITANCE_MAP[source_type]:
            inheritable_params.update(INHERITANCE_MAP[source_type][None])
    
    # Only include parameters that are actually in the source
    result = {}
    for param_name in inheritable_params:
        if param_name in source_component.params:
            result[param_name] = source_component.params[param_name]
            
        # Check for alternate parameter names
        for name_group in PARAMETER_NAME_MAP.values():
            if param_name in name_group:
                for alt_name in name_group:
                    if alt_name != param_name and alt_name in source_component.params:
                        result[param_name] = source_component.params[alt_name]
                        break
    
    return result


def get_all_inheritable_parameters(components, target_component) -> Tuple[Dict[str, Any], List[str]]:
    """
    Get all inheritable parameters from a list of components to a target component.
    
    Args:
        components: List of components with parameters to inherit
        target_component: Target component to inherit parameters to
        
    Returns:
        Tuple of (parameters dict, source component names)
    """
    all_params = {}
    source_names = []
    
    for component in components:
        inheritable = get_inheritable_parameters(component, target_component)
        if inheritable:
            all_params.update(inheritable)
            source_names.append(component.name)
    
    return all_params, source_names


def find_connected_components(component, direction: str = "input") -> List:
    """
    Find components connected to the specified component.
    
    Args:
        component: Component to find connections for
        direction: Either "input" (components connected to inputs) or "output" (components connected to outputs)
        
    Returns:
        List of connected components
    """
    if not component:
        return []
        
    connected_components = []
    
    if direction == "input":
        for port in component.input_ports:
            for comp, _ in port.connected_to:
                connected_components.append(comp)
    else: # "output"
        for port in component.output_ports:
            for comp, _ in port.connected_to:
                connected_components.append(comp)
                
    return connected_components


def map_parameter_names(param_name: str, component_type: ComponentType) -> List[str]:
    """
    Map a parameter name to equivalent names in the target component type.
    
    Args:
        param_name: Original parameter name
        component_type: Target component type
        
    Returns:
        List of equivalent parameter names for the target component
    """
    # Check if this parameter is in a name group
    for name_group in PARAMETER_NAME_MAP.values():
        if param_name in name_group:
            return name_group
            
    # Otherwise just return the original name
    return [param_name]


def find_components_for_parameter_propagation(source_component, parameter_name, other_components) -> List[Tuple[Any, List[str]]]:
    """
    Find components that can receive updates for a given parameter.
    
    Args:
        source_component: The component whose parameter was updated
        parameter_name: The name of the parameter that was updated
        other_components: List of other components to check for parameter propagation
        
    Returns:
        List of (component, param_names) tuples where component is a component that can 
        receive the parameter update, and param_names is a list of parameter names in that 
        component that correspond to the source parameter
    """
    if not source_component or not parameter_name or not other_components:
        return []
    
    if not hasattr(source_component, 'component_type'):
        return []
    
    source_type = source_component.component_type
    affected_components = []
    
    # Check for mappable parameter names
    target_param_names = map_parameter_names(parameter_name, source_type)
    
    # Debug logging
    print(f"[DEBUG] Looking for components that can receive {parameter_name}")
    print(f"[DEBUG] Source component type: {source_type.name}")
    print(f"[DEBUG] Mapped parameter names: {target_param_names}")
    print(f"[DEBUG] Number of other components to check: {len(other_components)}")
    
    # Check each component if it can receive this parameter
    for component in other_components:
        if not hasattr(component, 'component_type'):
            continue
            
        target_type = component.component_type
        
        # Skip if this component doesn't have params attribute at all
        if not hasattr(component, 'params'):
            component.params = {}  # Initialize empty params
            
        # Find parameters that can be propagated from source to this component
        can_propagate = False
        mapped_param_names = []
        
        # Check if there's a direct mapping in the inheritance map
        if source_type in INHERITANCE_MAP:
            # Check specific mapping for this target
            if target_type in INHERITANCE_MAP[source_type]:
                inheritable_params = INHERITANCE_MAP[source_type][target_type]
                if parameter_name in inheritable_params:
                    can_propagate = True
                    mapped_param_names = target_param_names
                    print(f"[DEBUG] {component.name} ({target_type.name}) can receive {parameter_name} via specific mapping")
            
            # Check generic mapping (None key)
            if None in INHERITANCE_MAP[source_type]:
                inheritable_params = INHERITANCE_MAP[source_type][None]
                if parameter_name in inheritable_params:
                    can_propagate = True
                    mapped_param_names = target_param_names
                    print(f"[DEBUG] {component.name} ({target_type.name}) can receive {parameter_name} via generic mapping")
        
        # If we found a mapping, add this component to the affected list
        if can_propagate and mapped_param_names:
            # Only include parameters that already exist in the target component's params
            # or that were explicitly set as inheritable for this component type
            existing_params = []
            for param_name in mapped_param_names:
                # We want to include the parameter if either:
                # 1. It already exists in the component
                # 2. Or it's defined as inheritable for this source->target type combination
                should_include = False
                
                # Check if it exists in the component already
                if hasattr(component, 'params') and param_name in component.params:
                    should_include = True
                    print(f"[DEBUG] {component.name} already has {param_name}")
                
                # Or check if it's explicitly defined as inheritable
                elif (source_type in INHERITANCE_MAP and
                      target_type in INHERITANCE_MAP[source_type] and
                      param_name in INHERITANCE_MAP[source_type][target_type]):
                    should_include = True
                    print(f"[DEBUG] {param_name} is explicitly inheritable by {component.name}")
                
                # For None (global) inheritance
                elif (source_type in INHERITANCE_MAP and
                      None in INHERITANCE_MAP[source_type] and 
                      param_name in INHERITANCE_MAP[source_type][None]):
                    should_include = True
                    print(f"[DEBUG] {param_name} is globally inheritable by {component.name}")
                
                if should_include:
                    existing_params.append(param_name)
            
            if existing_params:
                print(f"[DEBUG] Adding {component.name} to affected components with params {existing_params}")
                affected_components.append((component, existing_params))
    
    print(f"[DEBUG] Found {len(affected_components)} affected components")
    return affected_components