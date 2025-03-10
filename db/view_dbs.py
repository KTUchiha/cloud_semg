import asyncio
import aiosqlite
import glob
import os

async def print_table_info(db_name):
    async with aiosqlite.connect(db_name) as db:
        async with db.execute("SELECT name FROM sqlite_master WHERE type='table';") as cursor:
            print(f"Tables in the database '{db_name}':")
            async for row in cursor:
                table_name = row[0]
                print(f"\nTable: {table_name}")

                # Print the table schema
                async with db.execute(f"PRAGMA table_info({table_name});") as schema_cursor:
                    print("Schema:")
                    async for schema_row in schema_cursor:
                        print(f"  {schema_row[1]} ({schema_row[2]})")
                
                # Print the number of rows
                async with db.execute(f"SELECT COUNT(*) FROM {table_name};") as count_cursor:
                    count_row = await count_cursor.fetchone()
                    print(f"Number of rows: {count_row[0]}")
                
                # Print the last few rows (e.g., the last 5 rows)
                print("Last few rows:")
                async with db.execute(f"SELECT * FROM {table_name} ORDER BY ROWID DESC LIMIT 5;") as data_cursor:
                    async for data_row in data_cursor:
                        print(data_row)

async def main():
    db_files = glob.glob("*.db")  # Find all .db files in the current directory
    if not db_files:
        print("No SQLite database files found in the current directory.")
        return

    for db_file in db_files:
        print(f"\nProcessing database file: {db_file}")
        await print_table_info(db_file)

if __name__ == "__main__":
    asyncio.run(main())
