import pandas as pd
import sqlite3

db = sqlite3.connect("EKB_source.db")
cursor = db.cursor()

xlsx = pd.read_excel("../../DataSet_EKB_200000.xlsx", sheet_name=0)
sql = xlsx.to_sql("EKB_source", db, index=False)

print(xlsx)
for i in dir(xlsx):
    print(i)