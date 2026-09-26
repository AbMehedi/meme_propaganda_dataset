import sqlite3, sys
sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect('propaganda_dataset.db')
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = [r[0] for r in cur.fetchall()]
print('TABLES:', tables)
print()
for t in tables:
    cur.execute(f'PRAGMA table_info("{t}")')
    cols = cur.fetchall()
    print(f'=== {t} ===')
    for c in cols:
        print(f'  {c[1]} ({c[2]})')
    cur.execute(f'SELECT COUNT(*) FROM "{t}"')
    print(f'  ROW COUNT: {cur.fetchone()[0]}')
    # Show sample row (col names only)
    cur.execute(f'SELECT * FROM "{t}" LIMIT 1')
    row = cur.fetchone()
    if row:
        print(f'  SAMPLE (first 3 cols): {row[:3]}')
    print()
conn.close()
