import sqlite3
import pandas as pd
import sys

# Increase display options for pandas
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)

def inspect_db():
    try:
        conn = sqlite3.connect('db.sqlite3')
        cursor = conn.cursor()
        
        target_tables = ['booking_cinema', 'booking_movie', 'booking_screen', 'booking_showtime', 'booking_seat']
        
        with open('sqlite_dump.txt', 'w', encoding='utf-8') as f:
            for table_name in target_tables:
                f.write(f"\n--- Data in {table_name} ---\n")
                try:
                    df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
                    if not df.empty:
                        f.write(df.to_string())
                    else:
                        f.write("(Empty)")
                except Exception as e:
                    f.write(f"Error reading {table_name}: {e}\n")
                f.write("\n" + "="*50 + "\n")

        conn.close()
        print("Dump complete.")
    except Exception as e:
        print(f"Error connecting to DB: {e}")

if __name__ == "__main__":
    inspect_db()
