import unittest
from service_policy import (ServicePolicyError, is_visible, set_visible,
                            visible_services)


class VisibilityTests(unittest.TestCase):
    def test_admin_sees_all_and_users_only_active(self):
        live = {"wa": ["4477"], "tg": ["99450"], "bolt": ["234"]}
        cfg = {}
        set_visible(cfg, "tg", False)
        self.assertEqual(list(visible_services(live, cfg)), ["wa", "bolt"])
        self.assertEqual(visible_services(live, cfg, admin=True), live)
        self.assertFalse(is_visible(cfg, "TG"))
        set_visible(cfg, "tg", True)
        self.assertTrue(is_visible(cfg, "tg"))

    def test_invalid_sids_do_not_enter_rules(self):
        cfg = {}
        with self.assertRaises(ServicePolicyError):
            set_visible(cfg, "../path", False)
        self.assertEqual(cfg, {})


if __name__ == "__main__":
    unittest.main()
