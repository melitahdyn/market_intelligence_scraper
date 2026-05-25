import gspread
import pandas as pd
import time
from oauth2client.service_account import ServiceAccountCredentials

class GoogleSheetsHandler:
    def __init__(self, cred_path, sheet_id):
        self.cred_path = cred_path
        self.sheet_id = sheet_id
        self.client = None
        self.sheet = None
        self.connect()

    def connect(self):
        try:
            scope = [
                "https://spreadsheets.google.com/feeds",
                "https://www.googleapis.com/auth/drive"
            ]
            creds = ServiceAccountCredentials.from_json_keyfile_name(self.cred_path, scope)
            self.client = gspread.authorize(creds)

            spreadsheet = self.client.open_by_key(self.sheet_id)
            self.sheet = spreadsheet.sheet1

            print("✅ Connected to Google Sheets")

        except Exception as e:
            print(f"❌ Connection error: {e}")

    def upload_dataframe(self, df, max_retries=3):
        if df.empty:
            print("⚠️ Data kosong, skip upload")
            return False

        data = df.astype(str).values.tolist()

        for attempt in range(max_retries):
            try:
                # header check
                if not self.sheet.get_all_values():
                    self.sheet.append_row(df.columns.tolist())

                self.sheet.append_rows(data)

                print(f"✅ Upload sukses ({len(data)} rows)")
                return True

            except Exception as e:
                print(f"⚠️ Upload gagal (attempt {attempt+1}): {e}")
                time.sleep(2)

        print("❌ Upload gagal total setelah retry")
        return False