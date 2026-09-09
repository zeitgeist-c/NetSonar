import unittest

from flow_utils import orient_flow


class CaptureDirectionTests(unittest.TestCase):
    def test_ipv4_outbound_uses_source_as_local_endpoint(self):
        flow = orient_flow("192.168.1.20", 50000, "8.8.8.8", 443, {"192.168.1.20"})
        self.assertEqual("outbound", flow["direction"])
        self.assertEqual(("192.168.1.20", 50000), (flow["local_ip"], flow["local_port"]))
        self.assertEqual(("8.8.8.8", 443), (flow["remote_ip"], flow["remote_port"]))

    def test_lan_inbound_uses_destination_as_local_endpoint(self):
        flow = orient_flow("192.168.1.30", 5353, "192.168.1.20", 62000, {"192.168.1.20"})
        self.assertEqual("inbound", flow["direction"])
        self.assertEqual(62000, flow["local_port"])
        self.assertEqual("192.168.1.30", flow["remote_ip"])

    def test_global_ipv6_and_scope_are_normalized(self):
        flow = orient_flow("2001:db8::10", 55000, "2606:4700:4700::1111", 443,
                           {"2001:db8::10%7"})
        self.assertEqual("outbound", flow["direction"])
        self.assertEqual("2001:db8::10", flow["local_ip"])

    def test_irrelevant_addresses_are_rejected(self):
        local = {"192.168.1.20"}
        self.assertIsNone(orient_flow("10.0.0.2", 1, "10.0.0.3", 2, local))
        self.assertIsNone(orient_flow("192.168.1.20", 1, "224.0.0.251", 5353, local))
        self.assertIsNone(orient_flow("0.0.0.0", 1, "192.168.1.20", 2, local))
        self.assertIsNone(orient_flow("192.168.1.20", 1, "255.255.255.255", 2, local))
        self.assertIsNone(orient_flow("192.168.1.20", 1, "192.168.1.255", 2, local,
                                      {"192.168.1.255"}))


if __name__ == "__main__":
    unittest.main()
