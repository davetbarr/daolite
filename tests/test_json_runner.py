"""Unit tests for the JSON pipeline runner and pipeline integration."""

import json
import os
import tempfile
import unittest

from daolite import ComponentType, Pipeline, PipelineComponent
from daolite.pipeline import json_runner


class TestJsonRunner(unittest.TestCase):
    def setUp(self):
        # Minimal valid pipeline JSON
        self.minimal_pipeline = {
            "components": [
                {"type": "CAMERA", "name": "Camera1", "params": {"n_pixels": 1000}},
                {
                    "type": "CENTROIDER",
                    "name": "Centroider1",
                    "params": {"n_valid_subaps": 10, "n_pix_per_subap": 16},
                },
            ],
            "connections": [{"start": "Camera1", "end": "Centroider1"}],
        }

    def test_run_pipeline_from_json(self):
        # Write minimal pipeline to a temp file
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            json.dump(self.minimal_pipeline, f)
            temp_path = f.name
        try:
            results = json_runner.run_pipeline_from_json(temp_path)
            self.assertIsNotNone(results)
        finally:
            os.unlink(temp_path)

    def test_invalid_component_type(self):
        pipeline = {
            "components": [{"type": "INVALID", "name": "BadComp"}],
            "connections": [],
        }
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            json.dump(pipeline, f)
            temp_path = f.name
        try:
            with self.assertRaises(KeyError):
                json_runner.run_pipeline_from_json(temp_path)
        finally:
            os.unlink(temp_path)

    def test_missing_function(self):
        pipeline = {
            "components": [
                {
                    "type": "CAMERA",
                    "name": "Camera1",
                    "params": {"camera_function": "NonExistentFunc"},
                }
            ],
            "connections": [],
        }
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            json.dump(pipeline, f)
            temp_path = f.name
        try:
            # Should raise TypeError when trying to call None as a function
            with self.assertRaises(TypeError):
                json_runner.run_pipeline_from_json(temp_path)
        finally:
            os.unlink(temp_path)

    def test_dependency_setting(self):
        pipeline = {
            "components": [
                {"type": "CAMERA", "name": "Camera1", "params": {"n_pixels": 1000}},
                {
                    "type": "CENTROIDER",
                    "name": "Centroider1",
                    "params": {"n_valid_subaps": 10, "n_pix_per_subap": 16},
                },
            ],
            "connections": [{"start": "Camera1", "end": "Centroider1"}],
        }
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            json.dump(pipeline, f)
            temp_path = f.name
        try:
            # Patch PipelineComponent to capture dependencies
            from unittest.mock import patch

            with patch("daolite.PipelineComponent"):
                json_runner.run_pipeline_from_json(temp_path)
                # Check that dependencies are set
                # (This is a smoke test; for full check, inspect the pipeline object)
        finally:
            os.unlink(temp_path)

    def test_missing_json_file(self):
        # Should raise FileNotFoundError
        with self.assertRaises(FileNotFoundError):
            json_runner.run_pipeline_from_json("/tmp/nonexistent_file.json")

    def test_malformed_json_content(self):
        # Write malformed JSON to a temp file
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("{ this is not valid json }")
            temp_path = f.name
        try:
            with self.assertRaises(json.JSONDecodeError):
                json_runner.run_pipeline_from_json(temp_path)
        finally:
            os.unlink(temp_path)

    def test_main_cli(self):
        # Patch sys.argv and run main
        import sys
        from unittest.mock import patch

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            json.dump(self.minimal_pipeline, f)
            temp_path = f.name
        try:
            test_args = ["json_runner.py", temp_path]
            with patch.object(sys, "argv", test_args):
                # Patch print to capture output
                with patch("builtins.print") as mock_print:
                    json_runner.main()
                    # Check that print was called with expected output
                    self.assertTrue(
                        any(
                            "Pipeline run complete." in str(call)
                            for call in mock_print.call_args_list
                        )
                    )
        finally:
            os.unlink(temp_path)


class TestPipelineIntegration(unittest.TestCase):
    def test_pipeline_execution_order(self):
        # Create a pipeline with two dependent components
        pipeline = Pipeline()
        comp1 = PipelineComponent(
            component_type=ComponentType.CAMERA,
            name="Camera1",
            compute=None,
            function=lambda **kwargs: "camera_result",
            params={},
            dependencies=[],
        )
        comp2 = PipelineComponent(
            component_type=ComponentType.CENTROIDER,
            name="Centroider1",
            compute=None,
            function=lambda **kwargs: "centroid_result",
            params={},
            dependencies=["Camera1"],
        )
        pipeline.add_component(comp1)
        pipeline.add_component(comp2)
        results = pipeline.run(debug=False)
        self.assertIn("Camera1", results)
        self.assertIn("Centroider1", results)
        self.assertEqual(results["Camera1"], "camera_result")
        self.assertEqual(results["Centroider1"], "centroid_result")


if __name__ == "__main__":
    unittest.main()
