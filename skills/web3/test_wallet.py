import unittest
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from skills.web3.wallet import Web3Agent


class TestWeb3AgentMock(unittest.TestCase):
    """All tests run in mock mode (no real RPC)."""

    def setUp(self):
        os.environ.pop("WEB3_RPC_URL", None)
        os.environ.pop("AGENT_WALLET_PRIVATE_KEY", None)
        self.agent = Web3Agent()

    def test_mock_mode_enabled(self):
        self.assertTrue(self.agent._mock)

    def test_get_address(self):
        result = self.agent.get_address()
        self.assertTrue(result["address"].startswith("0x"))
        self.assertTrue(result["mock"])

    def test_generate_wallet(self):
        wallet = self.agent.generate_wallet()
        self.assertTrue(wallet["address"].startswith("0x"))
        self.assertTrue(wallet["private_key"].startswith("0x"))
        self.assertEqual(len(wallet["private_key"]), 66)  # 0x + 64 hex chars

    def test_get_balance(self):
        addr = self.agent._mock_address
        result = self.agent.get_balance(addr)
        self.assertEqual(result["eth"], 10.0)
        self.assertTrue(result["mock"])

    def test_send_transaction(self):
        to = "0x" + "ab" * 20
        tx = self.agent.send_transaction(to=to, value_eth=1.0)
        self.assertEqual(tx["status"], "confirmed")
        self.assertEqual(tx["value_eth"], 1.0)
        self.assertTrue(tx["hash"].startswith("0x"))

        # Balance should have decreased
        sender_bal = self.agent.get_balance(self.agent._mock_address)
        self.assertEqual(sender_bal["eth"], 9.0)

    def test_get_transaction(self):
        to = "0x" + "cd" * 20
        tx = self.agent.send_transaction(to=to, value_eth=0.5)
        found = self.agent.get_transaction(tx["hash"])
        self.assertEqual(found["hash"], tx["hash"])

    def test_call_contract(self):
        result = self.agent.call_contract(
            address="0x" + "ee" * 20,
            abi=[],
            function="balanceOf",
            args=["0x" + "ff" * 20]
        )
        self.assertEqual(result["function"], "balanceOf")
        self.assertTrue(result["mock"])

    def test_write_contract(self):
        result = self.agent.write_contract(
            address="0x" + "aa" * 20,
            abi=[],
            function="transfer",
            args=["0x" + "bb" * 20, 1000]
        )
        self.assertEqual(result["status"], "confirmed")
        self.assertTrue(result["hash"].startswith("0x"))

    def test_estimate_gas(self):
        result = self.agent.estimate_gas(to="0x" + "cc" * 20, value_eth=1.0)
        self.assertEqual(result["gas_estimate"], 21000)
        self.assertGreater(result["estimated_cost_eth"], 0)

    def test_transaction_history(self):
        self.agent.send_transaction(to="0x" + "11" * 20, value_eth=0.1)
        self.agent.send_transaction(to="0x" + "22" * 20, value_eth=0.2)
        history = self.agent.get_history()
        self.assertEqual(len(history), 2)


if __name__ == "__main__":
    unittest.main()
