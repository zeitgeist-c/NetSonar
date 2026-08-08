import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import kill_switch
from database import Database


class FirewallAtomicTests(unittest.TestCase):
    def test_second_direction_failure_rolls_back_first(self):
        calls = []
        def runner(command):
            calls.append(command)
            if "add" in command and "dir=in" in command:
                return False, "in failed"
            return True, "ok"
        with patch.object(kill_switch, "_run", side_effect=runner):
            self.assertFalse(kill_switch.block_ip("8.8.8.8"))
        rule_base = kill_switch._rule_base_for_ip("8.8.8.8")[1]
        self.assertTrue(any("delete" in call and f"name={rule_base}_out" in call
                            for call in calls))

    def test_unblock_success_removes_database_record(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Database(Path(directory) / "firewall.db")
            db.add_blocked_ip("8.8.8.8", "test")
            with patch.object(kill_switch, "_run", return_value=(True, "ok")):
                self.assertTrue(kill_switch.unblock_ip("8.8.8.8", db=db))
            self.assertEqual([], db.get_blocked_ips())
            db.close()

    def test_listing_accepts_only_complete_group_pairs(self):
        eight = kill_switch._rule_base_for_ip("8.8.8.8")[1]
        one = kill_switch._rule_base_for_ip("1.1.1.1")[1]
        names = [f"{eight}_out", f"{eight}_in", f"{one}_out", "OtherRule"]
        with patch.object(kill_switch, "_run", return_value=(True, json.dumps(names))):
            self.assertEqual(["8.8.8.8"], kill_switch.list_blocked())

    def test_query_failure_does_not_delete_database_state(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Database(Path(directory) / "reconcile.db")
            db.add_blocked_ip("8.8.8.8", "test")
            with patch.object(kill_switch, "_run", return_value=(False, "denied")):
                result = kill_switch.reconcile_firewall(db)
            self.assertTrue(result["skipped"])
            self.assertEqual("8.8.8.8", db.get_blocked_ips()[0]["ip"])
            db.close()


if __name__ == "__main__":
    unittest.main()
