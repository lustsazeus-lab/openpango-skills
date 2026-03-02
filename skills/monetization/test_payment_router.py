import unittest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from payment_router import PaymentRouter, Currency, EscrowStatus

class TestPaymentRouter(unittest.TestCase):
    def setUp(self):
        self.wallet = PaymentRouter()

    def test_mock_initialization(self):
        # By default in CI environment, it should boot into mock mode
        self.assertTrue(self.wallet._mock_mode)
        
    def test_lock_funds(self):
        eid = self.wallet.lock_funds(10.0, Currency.USD, "agent-123", "Test scraping bounty")
        self.assertIn(eid, self.wallet._escrows)
        escrow = self.wallet._escrows[eid]
        self.assertEqual(escrow["status"], EscrowStatus.LOCKED)
        self.assertEqual(escrow["amount"], 10.0)

    def test_invalid_amount(self):
        with self.assertRaises(ValueError):
            self.wallet.lock_funds(0, Currency.USD, "agent-123")
            
        with self.assertRaises(ValueError):
            self.wallet.lock_funds(-5.0, Currency.USDC, "agent-123")

    def test_fiat_release(self):
        eid = self.wallet.lock_funds(50.0, Currency.USD, "agent-writer", "Article generation")
        receipt = self.wallet.release_funds(eid)
        
        # Verify receipt
        self.assertIsNotNone(receipt)
        self.assertEqual(receipt["rail"], "fiat/stripe")
        self.assertEqual(receipt["status"], "success")
        
        # Verify escrow state changed
        self.assertEqual(self.wallet._escrows[eid]["status"], EscrowStatus.RELEASED)
        
    def test_crypto_release(self):
        eid = self.wallet.lock_funds(2.50, Currency.USDC, "agent-scraper", "Data extraction")
        receipt = self.wallet.release_funds(eid)
        
        # Verify receipt
        self.assertIsNotNone(receipt)
        self.assertEqual(receipt["rail"], "crypto/evm")
        self.assertEqual(receipt["status"], "success")
        
        # Verify escrow state changed
        self.assertEqual(self.wallet._escrows[eid]["status"], EscrowStatus.RELEASED)

    def test_double_release(self):
        eid = self.wallet.lock_funds(5.0, Currency.ETH, "agent-123")
        self.wallet.release_funds(eid)
        
        # Trying to release already released funds should raise ValueError
        with self.assertRaises(ValueError):
            self.wallet.release_funds(eid)

    def test_refund(self):
        eid = self.wallet.lock_funds(15.0, Currency.USDC, "agent-123")
        res = self.wallet.refund_escrow(eid, "Task failed SLA")
        
        self.assertEqual(res["action"], "refunded")
        self.assertEqual(self.wallet._escrows[eid]["status"], EscrowStatus.REFUNDED)
        self.assertEqual(self.wallet._escrows[eid]["refund_reason"], "Task failed SLA")

        # Can't release refunded funds
        with self.assertRaises(ValueError):
            self.wallet.release_funds(eid)

if __name__ == '__main__':
    unittest.main()
