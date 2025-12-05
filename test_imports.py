"""
Quick test to verify all imports work correctly
"""

print("Testing imports...")

try:
    import requests
    print("✓ requests")
except ImportError as e:
    print(f"✗ requests: {e}")

try:
    from requests.auth import HTTPBasicAuth
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    print("✓ requests components")
except ImportError as e:
    print(f"✗ requests components: {e}")

try:
    import json
    print("✓ json")
except ImportError as e:
    print(f"✗ json: {e}")

try:
    from datetime import datetime
    print("✓ datetime")
except ImportError as e:
    print(f"✗ datetime: {e}")

try:
    from collections import defaultdict
    print("✓ collections")
except ImportError as e:
    print(f"✗ collections: {e}")

try:
    import csv
    print("✓ csv")
except ImportError as e:
    print(f"✗ csv: {e}")

try:
    from pathlib import Path
    print("✓ pathlib")
except ImportError as e:
    print(f"✗ pathlib: {e}")

try:
    import os
    print("✓ os")
except ImportError as e:
    print(f"✗ os: {e}")

try:
    import argparse
    print("✓ argparse")
except ImportError as e:
    print(f"✗ argparse: {e}")

try:
    from tqdm import tqdm
    print("✓ tqdm")
except ImportError as e:
    print(f"✗ tqdm: {e}")

try:
    from dotenv import load_dotenv
    print("✓ python-dotenv")
except ImportError as e:
    print(f"✗ python-dotenv: {e}")

try:
    from concurrent.futures import ThreadPoolExecutor, as_completed
    print("✓ concurrent.futures")
except ImportError as e:
    print(f"✗ concurrent.futures: {e}")

try:
    import pickle
    print("✓ pickle")
except ImportError as e:
    print(f"✗ pickle: {e}")

try:
    import hashlib
    print("✓ hashlib")
except ImportError as e:
    print(f"✗ hashlib: {e}")

try:
    import time
    print("✓ time")
except ImportError as e:
    print(f"✗ time: {e}")

try:
    import logging
    from logging.handlers import RotatingFileHandler
    print("✓ logging with RotatingFileHandler")
except ImportError as e:
    print(f"✗ logging: {e}")

try:
    import openpyxl
    from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
    from openpyxl.utils import get_column_letter
    print("✓ openpyxl with styles")
except ImportError as e:
    print(f"✗ openpyxl: {e}")

print("\nAll imports tested!")
