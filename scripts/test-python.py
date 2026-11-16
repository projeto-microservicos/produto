"""Run Linux release-script tests in their supported environment, including on Windows."""
import subprocess
import sys

subprocess.run([sys.executable, "-m", "pip", "install", "-r", "services/exchange/requirements-dev.txt"], check=True)
subprocess.run([sys.executable, "-m", "pytest", "--import-mode=importlib", "-p", "no:cacheprovider", "-q",
                "services/exchange/tests", "services/exchange/tests_ci", "services/order/tests_ci"], check=True)
