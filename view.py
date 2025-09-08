import sqlite3
conn=sqlite3.connect("luggage.db")
cursor=conn.cursor()
print("columns in luggage.db")
cursor.execute("select name from sqlite_master where type='table';")
tables=cursor.fetchall()
print(tables)
try:
    cursor.execute("select*from users;")
    rows=cursor.fetchall()
    print("users table")
    for row in rows:
        print(row)
except:
    print("table users dosn texists")

try:
    cursor.execute("select *from luggage;")
    rows=cursor.fetchall()
    for row in rows:
        print(row)
except:
    print("table luggage dosnt exists")
try:
    cursor.execute("select*from found_reports;")
    rows=cursor.fetchall()
    print("table found_report is")
    for row in rows:
        print(row)
except:
    print("found_luggage table dosnt exist")
try:
    cursor.execute("select*from lost_reports;")
    rows=cursor.fetchall()
    print("table lost_report is")
    for row in rows:
        print(row)
except:
    print("lostreports dosnt exists")
try:
    cursor.execute(f"PRAGMA table_info(found_reports);")
    columns = cursor.fetchall()
    for col in columns:
        print(col) 
except:
    print("table not exits")