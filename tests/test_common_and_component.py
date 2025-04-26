import unittest
from daolite.component import Component
from daolite.common import ComponentType, ResourceId, ComponentId


class TestComponentBase(unittest.TestCase):
    def test_component_instantiation(self):
        comp = Component()
        self.assertIsInstance(comp, Component)

    def test_process_returns_input(self):
        comp = Component()
        data = [1, 2, 3]
        self.assertEqual(comp.process(data), data)
        self.assertIs(comp.process(data), data)  # Should be same object

    def test_subclass_process_override(self):
        class MyComponent(Component):
            def process(self, data=None):
                return "processed"

        comp = MyComponent()
        self.assertEqual(comp.process([1, 2]), "processed")


class TestComponentTypeEnum(unittest.TestCase):
    def test_enum_members_exist(self):
        self.assertTrue(hasattr(ComponentType, "CAMERA"))
        self.assertTrue(hasattr(ComponentType, "CALIBRATION"))
        self.assertTrue(hasattr(ComponentType, "CENTROIDER"))
        self.assertTrue(hasattr(ComponentType, "RECONSTRUCTION"))
        self.assertTrue(hasattr(ComponentType, "CONTROL"))
        self.assertTrue(hasattr(ComponentType, "NETWORK"))
        self.assertTrue(hasattr(ComponentType, "DM"))
        self.assertTrue(hasattr(ComponentType, "OTHER"))

    def test_enum_members_are_unique(self):
        values = set(item.value for item in ComponentType)
        self.assertEqual(len(values), len(ComponentType))


class TestTypeAliases(unittest.TestCase):
    def test_resource_id_type(self):
        rid: ResourceId = "cpu0"
        self.assertIsInstance(rid, str)

    def test_component_id_type(self):
        cid: ComponentId = "comp1"
        self.assertIsInstance(cid, str)


if __name__ == "__main__":
    unittest.main()
