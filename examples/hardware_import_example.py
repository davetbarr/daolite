# Example: Import/define hardware resources from file (YAML)
from daolite.compute import create_compute_resources_from_yaml

custom_cpu = create_compute_resources_from_yaml("examples/custom_cpu.yaml")
print("Imported custom CPU:", custom_cpu)
