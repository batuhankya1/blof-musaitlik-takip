import sys
import os

# Ana dizini sys.path'e ekle
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app import app

# Vercel Serverless Function entry point
# Flask wsgi callable nesnesini dışa aktarır
