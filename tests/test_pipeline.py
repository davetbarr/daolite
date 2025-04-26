import unittest
import numpy as np
from daolite.pipeline.pipeline import Pipeline, PipelineComponent
from daolite.common import ComponentType
from daolite.compute import create_compute_resources

def dummy_func(**kwargs):
    # Returns a scalar or array depending on input
    if 'start_times' in kwargs and kwargs['start_times'] is not None:
        st = kwargs['start_times']
        arr = np.zeros_like(st)
        arr[:, 0] = st[:, 1]
        arr[:, 1] = st[:, 1] + 1
        return arr
    return 1.0

class TestPipeline(unittest.TestCase):
    def setUp(self):
        self.compute = create_compute_resources(
            cores=2, core_frequency=1e9, flops_per_cycle=2,
            memory_channels=1, memory_width=32, memory_frequency=1e9,
            network_speed=1e9, time_in_driver=1)

    def test_add_and_run_pipeline(self):
        pipeline = Pipeline()
        cam = PipelineComponent(
            component_type=ComponentType.CAMERA,
            name="Camera",
            compute=self.compute,
            function=dummy_func,
            params={}
        )
        proc = PipelineComponent(
            component_type=ComponentType.CENTROIDER,
            name="Proc",
            compute=self.compute,
            function=dummy_func,
            params={},
            dependencies=["Camera"]
        )
        pipeline.add_component(cam)
        pipeline.add_component(proc)
        results = pipeline.run()
        self.assertIn("Camera", results)
        self.assertIn("Proc", results)

    def test_duplicate_component_name(self):
        pipeline = Pipeline()
        cam1 = PipelineComponent(
            component_type=ComponentType.CAMERA,
            name="Camera",
            compute=self.compute,
            function=dummy_func,
            params={}
        )
        cam2 = PipelineComponent(
            component_type=ComponentType.CAMERA,
            name="Camera",
            compute=self.compute,
            function=dummy_func,
            params={}
        )
        pipeline.add_component(cam1)
        with self.assertRaises(ValueError):
            pipeline.add_component(cam2)

    def test_circular_dependency(self):
        pipeline = Pipeline()
        a = PipelineComponent(
            component_type=ComponentType.CAMERA,
            name="A",
            compute=self.compute,
            function=dummy_func,
            params={},
            dependencies=["B"]
        )
        b = PipelineComponent(
            component_type=ComponentType.CENTROIDER,
            name="B",
            compute=self.compute,
            function=dummy_func,
            params={},
            dependencies=["A"]
        )
        pipeline.add_component(a)
        pipeline.add_component(b)
        with self.assertRaises(ValueError):
            pipeline.run()

    def test_visualize_before_run(self):
        pipeline = Pipeline()
        cam = PipelineComponent(
            component_type=ComponentType.CAMERA,
            name="Camera",
            compute=self.compute,
            function=dummy_func,
            params={}
        )
        pipeline.add_component(cam)
        with self.assertRaises(ValueError):
            pipeline.visualize()

    def test_visualize_smoke(self):
        pipeline = Pipeline()
        cam = PipelineComponent(
            component_type=ComponentType.CAMERA,
            name="Camera",
            compute=self.compute,
            function=dummy_func,
            params={}
        )
        proc = PipelineComponent(
            component_type=ComponentType.CENTROIDER,
            name="Proc",
            compute=self.compute,
            function=dummy_func,
            params={},
            dependencies=["Camera"]
        )
        pipeline.add_component(cam)
        pipeline.add_component(proc)
        pipeline.run()
        fig, ax, latency = pipeline.visualize()
        self.assertIsNotNone(fig)
        self.assertIsNotNone(ax)
        self.assertIsInstance(latency, (int, float, np.floating))

if __name__ == "__main__":
    unittest.main()
