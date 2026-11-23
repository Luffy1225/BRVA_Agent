import unittest
import os
import shutil
from pathlib import Path

class TestPodmanContainerization(unittest.TestCase):
    """
    Test suite for Podman containerization standards, Containerfile integrity,
    compose configuration, helper scripts, and runtime health readiness as required by Assignment 2.
    """

    @classmethod
    def setUpClass(cls):
        cls.root_dir = Path(__file__).resolve().parent.parent
        cls.containerfile_path = cls.root_dir / "Containerfile"
        cls.dockerfile_path = cls.root_dir / "Dockerfile"
        cls.compose_path = cls.root_dir / "podman-compose.yml"
        cls.containerignore_path = cls.root_dir / ".containerignore"
        cls.dockerignore_path = cls.root_dir / ".dockerignore"
        cls.req_path = cls.root_dir / "requirements.txt"
        cls.env_example_path = cls.root_dir / ".env.example"
        cls.run_sh_path = cls.root_dir / "scripts" / "run_podman.sh"
        cls.run_ps1_path = cls.root_dir / "scripts" / "run_podman.ps1"

    def test_containerfile_exists_and_standards(self):
        self.assertTrue(self.containerfile_path.exists(), "Containerfile must exist in project root")
        content = self.containerfile_path.read_text(encoding="utf-8")

        # 1. Base image specification
        self.assertIn("FROM", content)
        self.assertTrue(
            "python:3.11-slim" in content or "python:3.11" in content,
            "Containerfile must use lightweight Python 3.11 slim image"
        )

        # 2. Non-root user compliance
        self.assertIn("useradd", content, "Containerfile must create non-root user")
        self.assertIn("USER aero", content, "Containerfile must switch to non-root user aero")

        # 3. Security & environment settings
        self.assertIn("PYTHONUNBUFFERED=1", content, "Must enable unbuffered stdout for container logging")
        self.assertIn("PYTHONPATH=/app", content, "Must configure PYTHONPATH=/app")

        # 4. Entrypoint / Command
        self.assertTrue(
            "streamlit" in content or "src.ui.cli" in content,
            "Container must specify web or cli entrypoint"
        )

    def test_dockerfile_and_ignore_parity(self):
        """Validates that Dockerfile, .containerignore, and .dockerignore exist for dual-engine compatibility."""
        self.assertTrue(self.dockerfile_path.exists(), "Dockerfile must exist for dual Docker/Podman compatibility")
        self.assertTrue(self.containerignore_path.exists(), ".containerignore must exist")
        self.assertTrue(self.dockerignore_path.exists(), ".dockerignore must exist")

        df_content = self.dockerfile_path.read_text(encoding="utf-8")
        self.assertIn("FROM", df_content)
        self.assertIn("USER aero", df_content)

    def test_podman_compose_structure(self):
        self.assertTrue(self.compose_path.exists(), "podman-compose.yml must exist")
        compose_content = self.compose_path.read_text(encoding="utf-8")

        self.assertIn("services:", compose_content)
        self.assertIn("8501:8501", compose_content, "Compose must expose Streamlit port 8501")
        self.assertIn("env_file:", compose_content, "Compose must link .env file")
        self.assertIn("aeroagent:v1", compose_content, "Compose must specify image tag aeroagent:v1")

    def test_podman_helper_scripts(self):
        """Ensures cross-platform execution helper scripts exist for TA / Professor."""
        self.assertTrue(self.run_sh_path.exists(), "scripts/run_podman.sh must exist for Linux/macOS evaluation")
        self.assertTrue(self.run_ps1_path.exists(), "scripts/run_podman.ps1 must exist for Windows evaluation")

        sh_content = self.run_sh_path.read_text(encoding="utf-8")
        self.assertIn("podman", sh_content)
        self.assertIn("aeroagent:v1", sh_content)

    def test_requirements_dependencies(self):
        self.assertTrue(self.req_path.exists(), "requirements.txt must exist")
        reqs = self.req_path.read_text(encoding="utf-8").lower()

        required_packages = ["pydantic", "pandas", "requests", "streamlit"]
        for pkg in required_packages:
            self.assertIn(pkg, reqs, f"requirements.txt must include {pkg}")

    def test_environment_template(self):
        self.assertTrue(self.env_example_path.exists(), ".env.example must exist")
        env_content = self.env_example_path.read_text(encoding="utf-8")

        expected_vars = ["GEMINI_API_KEY", "BRVA_API_BASE_URL", "BRVA_AGENT_API_KEY"]
        for var_name in expected_vars:
            self.assertIn(var_name, env_content, f".env.example must declare {var_name}")

    def test_data_assets_availability_for_container(self):
        data_dir = self.root_dir / "data"
        self.assertTrue((data_dir / "local_fallback_routes.csv").exists(), "local_fallback_routes.csv must exist")
        self.assertTrue((data_dir / "sample_flight_pass.csv").exists(), "sample_flight_pass.csv must exist")
        self.assertTrue((data_dir / "sample_flight_fail.csv").exists(), "sample_flight_fail.csv must exist")

    def test_entrypoint_modules_importability(self):
        """Validates that CLI and Web modules are valid and importable for container execution."""
        import importlib
        cli_mod = importlib.import_module("src.ui.cli")
        self.assertTrue(hasattr(cli_mod, "main"), "src.ui.cli must have main() entrypoint")
        
        web_file = self.root_dir / "src" / "ui" / "web.py"
        self.assertTrue(web_file.exists(), "src/ui/web.py must exist for Streamlit mode")

    def test_offline_container_readiness(self):
        """Validates that the agent can initialize and run in container offline mode without API keys."""
        from src.agent import AeroAgent
        from src.llm import OfflineRuleProvider
        from src.memory import AgentMemory

        agent = AeroAgent(memory=AgentMemory(), llm_provider=OfflineRuleProvider())
        resp = agent.run("你好")
        self.assertIn("機長您好", resp)

if __name__ == "__main__":
    unittest.main()
