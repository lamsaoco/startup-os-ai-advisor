from ingestion.loader import get_connection
from pgvector.psycopg2 import register_vector
import json
import numpy as np

def main():
    conn = get_connection()
    register_vector(conn)
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM chunks")
        n = cur.fetchone()[0]
        print(f"Total chunks: {n}")
        if n == 0:
            print("DB is empty!")
            return
            
        cur.execute("SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'chunks' AND indexname LIKE '%embedding%'")
        for row in cur.fetchall():
            print(f"Index: {row[0]}")
            print(f"Def: {row[1]}")
            
        cur.execute("SHOW ivfflat.probes")
        print(f"ivfflat.probes: {cur.fetchone()[0]}")
        
        # Test vector search vs sequential scan
        cur.execute("SELECT chunk_id, embedding FROM chunks LIMIT 1")
        row = cur.fetchone()
        chunk_id = row[0]
        sample_vec = row[1]
        
        cur.execute("SET enable_indexscan = off")
        cur.execute("SET enable_bitmapscan = off")
        cur.execute("SELECT chunk_id FROM chunks ORDER BY embedding <=> %s::vector LIMIT 5", (sample_vec,))
        seq_results = [r[0] for r in cur.fetchall()]
        
        cur.execute("SET enable_indexscan = on")
        cur.execute("SET enable_bitmapscan = on")
        cur.execute("SET ivfflat.probes = 1")
        cur.execute("SELECT chunk_id FROM chunks ORDER BY embedding <=> %s::vector LIMIT 5", (sample_vec,))
        idx_1 = [r[0] for r in cur.fetchall()]
        
        print("SeqScan vs Index(probes=1) match:", seq_results == idx_1)
        print("Seq:", seq_results)
        print("Idx:", idx_1)
        
    conn.close()

if __name__ == "__main__":
    main()
