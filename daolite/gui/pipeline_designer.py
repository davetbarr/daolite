from daolite.gui.designer.pipeline_designer import PipelineDesignerApp
import sys

if __name__ == "__main__":
    # Accept optional JSON file argument
    json_path = sys.argv[1] if len(sys.argv) > 1 else None
    PipelineDesignerApp.run(json_path)