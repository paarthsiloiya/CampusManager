import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    print('DATABASE_URL not set')
    raise SystemExit(1)

print('Connecting using:', DATABASE_URL)
engine = create_engine(DATABASE_URL, echo=False)

with engine.connect() as conn:
    res = conn.execute(text('SELECT current_user, session_user'))
    print('current_user, session_user ->', res.fetchone())

    res = conn.execute(text("SELECT nspname, pg_get_userbyid(nspowner) AS owner FROM pg_namespace WHERE nspname='public'"))
    print('public schema owner ->', res.fetchone())

    res = conn.execute(text("SELECT has_schema_privilege(current_user, 'public', 'CREATE') as can_create, has_schema_privilege(current_user, 'public', 'USAGE') as can_usage"))
    print('schema privileges ->', res.fetchone())

    res = conn.execute(text("SELECT rolname, rolsuper FROM pg_roles WHERE rolname = current_user"))
    print('role info ->', res.fetchone())

    # Try to create a temporary type (will fail if no permission)
    try:
        conn.execute(text("CREATE TYPE __tmp_test_enum AS ENUM ('X')"))
        print('CREATE TYPE succeeded; dropping...')
        conn.execute(text("DROP TYPE __tmp_test_enum"))
    except Exception as e:
        print('CREATE TYPE failed:', e)
