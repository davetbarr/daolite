.. _api_control:

Control API Reference
=====================

This page documents the API for the control components in DaoLITE.

Control Module
--------------

.. automodule:: daolite.pipeline.control
   :members:
   :undoc-members:
   :show-inheritance:

Control Functions
-----------------

.. autofunction:: daolite.pipeline.control.integrator_control

.. autofunction:: daolite.pipeline.control.leaky_integrator_control

.. autofunction:: daolite.pipeline.control.dm_control

.. autofunction:: daolite.pipeline.control.predictive_control

.. autofunction:: daolite.pipeline.control.modal_control

.. autofunction:: daolite.pipeline.control.lqg_control

.. autofunction:: daolite.pipeline.control.gain_optimization

.. autofunction:: daolite.pipeline.control.command_clipping

Control Classes
---------------

.. autoclass:: daolite.pipeline.control.ControllerBase
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: daolite.pipeline.control.IntegratorController
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: daolite.pipeline.control.LQGController
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: daolite.pipeline.control.ModalController
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: daolite.pipeline.control.PredictiveController
   :members:
   :undoc-members:
   :show-inheritance: