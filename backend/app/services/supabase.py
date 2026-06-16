import os
from supabase import create_client, Client

url: str = os.getenv("SUPABASE_URL", "")
key: str = os.getenv("SUPABASE_SERVICE_KEY", "")
supabase: Client = create_client(url, key)


class SupabaseService:
    def __init__(self):
        self.client = supabase

    def insert(self, table: str, data: dict):
        return self.client.table(table).insert(data).execute()

    def upsert(self, table: str, data: dict, on_conflict: str = "id"):
        return self.client.table(table).upsert(data, on_conflict=on_conflict).execute()

    def update(self, table: str, data: dict, match_column: str, match_value: str):
        return self.client.table(table).update(data).eq(match_column, match_value).execute()

    def delete(self, table: str, match_column: str, match_value: str):
        return self.client.table(table).delete().eq(match_column, match_value).execute()

    def select(self, table: str, match_column: str = None, match_value: str = None):
        query = self.client.table(table).select("*")
        if match_column and match_value:
            query = query.eq(match_column, match_value)
        return query.execute()

    def select_by_id(self, table: str, record_id: str):
        return self.client.table(table).select("*").eq("id", record_id).execute()


db = SupabaseService()
