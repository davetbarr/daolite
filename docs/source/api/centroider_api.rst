.. _api_centroider:

Centroider API Reference
========================

This page documents the API for the centroiding components in daolite.

Centroider Module
-----------------

.. automodule:: daolite.pipeline.centroider
   :members:
   :undoc-members:
   :show-inheritance:

Centroider Functions
--------------------

.. autofunction:: daolite.pipeline.centroider.center_of_gravity

.. autofunction:: daolite.pipeline.centroider.weighted_center_of_gravity

.. autofunction:: daolite.pipeline.centroider.cross_correlation_centroider

.. autofunction:: daolite.pipeline.centroider.square_difference_centroider

.. autofunction:: daolite.pipeline.centroider.matched_filter_centroider

.. autofunction:: daolite.pipeline.centroider.pyramid_centroider

.. autofunction:: daolite.pipeline.centroider.quad_cell_centroider

Centroider Classes
------------------

.. autoclass:: daolite.pipeline.centroider.CentroiderBase
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: daolite.pipeline.centroider.ShackHartmannCentroider
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: daolite.pipeline.centroider.PyramidWavefrontSensor
   :members:
   :undoc-members:
   :show-inheritance: