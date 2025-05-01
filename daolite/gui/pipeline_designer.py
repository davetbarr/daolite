from daolite.gui.designer.pipeline_designer import PipelineDesignerApp

if __name__ == "__main__":
    PipelineDesignerApp.run()

    def _add_component(self, comp_type: ComponentType):
        """
        Add a new component to the scene.

        Args:
            comp_type: Type of component to add
        """
        # Generate a unique name
        self.component_counts[comp_type] += 1
        name = f"{comp_type.value}{self.component_counts[comp_type]}"

        # Create the component
        component = ComponentBlock(comp_type, name)

        # Set default for CENTROIDER n_pix_per_subap
        if comp_type == ComponentType.CENTROIDER:
            if "n_pix_per_subap" not in component.params:
                component.params["n_pix_per_subap"] = 16

        # Position at center of view
        view_center = self.view.mapToScene(self.view.viewport().rect().center())
        component.setPos(view_center.x() - 90, view_center.y() - 40)

        # Add to scene
        self.scene.addItem(component)

        # For components needing a compute resource, prompt for it
        if comp_type != ComponentType.NETWORK:  # Network uses sources/targets compute
            component.compute = self._get_default_compute_for_type(comp_type)
