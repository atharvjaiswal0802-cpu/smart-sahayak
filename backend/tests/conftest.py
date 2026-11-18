import os, sys, tempfile
os.environ["SAHAYAK_DB"] = os.path.join(tempfile.mkdtemp(), "t.db")
os.environ["ADMIN_KEY"] = "test-key"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ["OTP_DEV_ECHO"] = "1"
