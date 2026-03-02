import unittest
import os
import sys
import sqlite3
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from registry_client import SkillRegistry

class TestSkillRegistry(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for the sqlite DB
        self.test_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.test_dir.name, "test_registry.sqlite")
        self.registry = SkillRegistry(db_path=self.db_path)

    def tearDown(self):
        self.test_dir.cleanup()

    def test_database_initialization(self):
        # Should seed with core skills
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT count(*) FROM skills")
            count = cursor.fetchone()[0]
            self.assertGreater(count, 0)

    def test_publish_and_search(self):
        # 1. Publish a new fake skill
        self.registry.publish(
            name="test-scraper",
            description="Extracts data from test sites",
            version="1.0.0",
            author="TestAgent",
            install_uri="github.com/testagent/scraper",
            capabilities=["web/testing", "data/extract"]
        )

        # 2. Search by name/description
        results = self.registry.search(query="scraper")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "test-scraper")
        
        # 3. Check capabilities parse properly
        self.assertIn("data/extract", results[0]["capabilities"])

    def test_search_core_skills(self):
        # The DB seeds with 'browser' and 'memory'
        results = self.registry.search(query="Playwright")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], "browser")

if __name__ == '__main__':
    unittest.main()
