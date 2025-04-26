.. _api_reconstruction:

Reconstruction API Reference
============================

This page documents the API for the wavefront reconstruction components in daolite.

Reconstruction Module
---------------------

.. automodule:: daolite.pipeline.reconstruction
   :members:
   :undoc-members:
   :show-inheritance:

Reconstruction Functions
------------------------

.. autofunction:: daolite.pipeline.reconstruction.mvm_reconstruction

.. autofunction:: daolite.pipeline.reconstruction.sparse_mvm_reconstruction

.. autofunction:: daolite.pipeline.reconstruction.cg_reconstruction

.. autofunction:: daolite.pipeline.reconstruction.fdpcg_reconstruction

.. autofunction:: daolite.pipeline.reconstruction.mvr_reconstruction

.. autofunction:: daolite.pipeline.reconstruction.zonal_reconstruction

.. autofunction:: daolite.pipeline.reconstruction.modal_reconstruction

.. autofunction:: daolite.pipeline.reconstruction.tomographic_reconstruction

.. autofunction:: daolite.pipeline.reconstruction.pyramid_reconstruction

Reconstruction Classes
----------------------

.. autoclass:: daolite.pipeline.reconstruction.ReconstructorBase
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: daolite.pipeline.reconstruction.MatrixVectorReconstructor
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: daolite.pipeline.reconstruction.SparseReconstructionMatrix
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: daolite.pipeline.reconstruction.IterativeReconstructor
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: daolite.pipeline.reconstruction.TomographicReconstructor
   :members:
   :undoc-members:
   :show-inheritance: