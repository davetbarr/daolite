class Component:
    """
    Base component class for the daolite pipeline.

    This is the foundational class for all components in the adaptive optics
    processing pipeline. Components can be arranged in sequence to perform
    operations like pixel calibration, centroiding, wavefront reconstruction,
    and deformable mirror control.

    Each component should override the process() method to implement its specific
    functionality.
    """

    def __init__(self) -> None:
        """
        Initialize a new Component instance.

        Creates a generic pipeline component with default settings.
        Subclasses should customize this method as needed.
        """

    def process(self, data=None):
        """
        Process data through this component.

        This is the main method that should be overridden by subclasses to
        implement specific processing functionality.

        Parameters
        ----------
        data : array_like, optional
            Input data to process

        Returns
        -------
        array_like
            Processed data
        """
        return data
