from daolite.gui.designer.pipeline_designer import PipelineDesignerApp
import sys
import tempfile
import logging

logfile = tempfile.NamedTemporaryFile(prefix="daolite_", suffix=".log", delete=False)
logging.basicConfig(filename=logfile.name, level=logging.INFO, filemode='w')
print(f"Logging to {logfile.name}")

def main():
    """
    Entry point for daolite-pipeline-designer console script.
    Accepts an optional JSON file argument from sys.argv.
    """
    json_path = sys.argv[1] if len(sys.argv) > 1 else None
    PipelineDesignerApp.run(json_path)

if __name__ == "__main__":
    main()