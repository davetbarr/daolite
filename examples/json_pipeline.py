# Run a pipeline from a JSON config file
import json
from daolite.pipeline.json_runner import run_pipeline_from_json
from daolite.pipeline.reconstruction import Reconstruction

results = run_pipeline_from_json("examples/config_example.json")
print("Pipeline results:", results)
# # Optionally visualize
# try:
#     from daolite.pipeline.pipeline import Pipeline, PipelineComponent, ComponentType
#     from daolite.pipeline.compute import nvidia_rtx_4090

#     pipeline = Pipeline.from_json(config)
#     pipeline.add_component(
#         PipelineComponent(
#             component_type=ComponentType.RECONSTRUCTION,
#             name="Reconstructor",
#             compute=nvidia_rtx_4090(),
#             function=Reconstruction,  # FIXED: was mvr_reconstruction
#             params={"n_slopes": n_valid_subaps * 2, "n_actuators": n_actuators},
#             dependencies=["Centroider"],
#         )
#     )
#     pipeline.visualize(
#         title="JSON Pipeline Timing", save_path="json_pipeline_timing.png"
#     )
# except Exception as e:
#     print("Visualization failed:", e)
