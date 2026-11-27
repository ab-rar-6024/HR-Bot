"""Create an HR account:  python scripts/create_user.py hr@company.com "Asha R" 'a-long-password'"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.db import init_db  # noqa: E402
from app.meet import auth  # noqa: E402

if len(sys.argv) != 4 or len(sys.argv[3]) < 10:
    sys.exit("usage: create_user.py EMAIL NAME PASSWORD(>=10 chars)")
init_db()
auth.create_user(sys.argv[1], sys.argv[2], "hr", sys.argv[3])
print("HR user created:", sys.argv[1])
