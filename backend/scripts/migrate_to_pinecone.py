import argparse
import sys
import os
import time

# Ensure backend is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Ensure we point to the canonical chroma_db, overriding any environment variables
os.environ["CHROMA_PERSIST_DIR"] = "./chroma_db"

from app.core import chroma
from app.core import config

def run_migration(dry_run: bool):
    print("MIGRATION SCRIPT STARTING\n")
    if dry_run:
        print("WARNING: This is a DRY RUN. No Pinecone connections will be made.")
    else:
        print("WARNING: ACTIVE MIGRATION. Modifying Pinecone resources.")

    print("WARNING: Reading from local Chroma database (read-only).\n")

    # 1. Initialize Pinecone if not dry run
    pc = None
    index = None
    if not dry_run:
        settings = config.get_settings()
        api_key = settings.PINECONE_API_KEY
        index_name = settings.PINECONE_INDEX_NAME
        if not api_key:
            print("FAIL: PINECONE_API_KEY is not set.")
            sys.exit(1)
        if not index_name:
            print("FAIL: PINECONE_INDEX_NAME is not set.")
            sys.exit(1)

        try:
            from pinecone import Pinecone, ServerlessSpec
            pc = Pinecone(api_key=api_key)

            # Check if index exists, else create
            existing_indexes = [idx["name"] for idx in pc.list_indexes()]
            if index_name not in existing_indexes:
                print(f"Index '{index_name}' not found. Creating...")
                pc.create_index(
                    name=index_name,
                    dimension=384,
                    metric="cosine",
                    spec=ServerlessSpec(
                        cloud="aws",
                        region="us-east-1"
                    )
                )
                print("Waiting for index to be ready...")
                while not pc.describe_index(index_name).status["ready"]:
                    time.sleep(1)
                print("Index is ready.")
            else:
                idx_info = pc.describe_index(index_name)
                if idx_info.dimension != 384 or idx_info.metric != "cosine":
                    print(f"FAIL: Index '{index_name}' exists but has invalid config (dim={idx_info.dimension}, metric={idx_info.metric}). Expected dim=384, metric=cosine.")
                    sys.exit(1)
                print(f"Index '{index_name}' exists and configuration is valid.")

            index = pc.Index(index_name)
        except Exception as e:
            print(f"FAIL: Pinecone initialization error: {e}")
            sys.exit(1)

    # 2. Initialize Chroma
    try:
        # Force chroma to re-evaluate the path if already imported
        chroma._settings.CHROMA_PERSIST_DIR = "./chroma_db"
        chroma.CHROMA_PATH = os.path.join(chroma._BACKEND_DIR, "chroma_db")
        client = chroma.get_chroma_client()
        collections = client.list_collections()
    except Exception as e:
        print(f"FAIL: Could not initialize Chroma client: {e}")
        sys.exit(1)

    print(f"\nCollections discovered: {len(collections)}\n")

    total_vectors = 0
    total_valid = 0
    total_skipped = 0

    # Store reports for namespaces
    # namespace -> {"raw": 0, "valid": 0, "skipped": 0, "pinecone": 0}
    namespace_reports = {}

    # Keep track of a few valid IDs to verify later
    verification_samples = {}

    for c in collections:
        ns_name = c.name
        try:
            count = c.count()
        except Exception as e:
            print(f"Error counting collection {ns_name}: {e}")
            sys.exit(1)

        print(f"Scanning collection/namespace: {ns_name} ({count} vectors)")
        namespace_reports[ns_name] = {"raw": count, "valid": 0, "skipped": 0, "pinecone": 0}

        batch_size = 500
        offset = 0

        while offset < count:
            results = c.get(
                limit=batch_size,
                offset=offset,
                include=["embeddings", "metadatas", "documents"]
            )

            ids = results.get("ids", [])
            embeddings = results.get("embeddings", [])
            metadatas = results.get("metadatas", [])
            documents = results.get("documents", [])

            pinecone_batch = []

            for i, vid in enumerate(ids):
                total_vectors += 1

                meta = metadatas[i] if metadatas and i < len(metadatas) else None
                doc = documents[i] if documents and i < len(documents) else None
                emb = embeddings[i] if embeddings and i < len(embeddings) else None

                # Validation checks
                skip_reason = None
                if meta is None:
                    skip_reason = "metadata is None"
                elif doc is None or not doc.strip():
                    skip_reason = "document is None or empty"
                elif emb is None:
                    skip_reason = "embedding is None"
                elif len(emb) != 384:
                    skip_reason = f"embedding dimension != 384 (was {len(emb)})"

                if skip_reason:
                    print(f"  Skipping record [Collection: {ns_name}, ID: {vid}] - Reason: {skip_reason}")
                    total_skipped += 1
                    namespace_reports[ns_name]["skipped"] += 1
                else:
                    total_valid += 1
                    namespace_reports[ns_name]["valid"] += 1

                    # Prepare valid record
                    meta_payload = dict(meta)
                    meta_payload["text"] = doc

                    pinecone_batch.append({
                        "id": vid,
                        "values": emb,
                        "metadata": meta_payload
                    })

                    if ns_name not in verification_samples:
                        verification_samples[ns_name] = vid

            # Upsert batch
            if pinecone_batch and not dry_run:
                try:
                    index.upsert(vectors=pinecone_batch, namespace=ns_name)
                except Exception as e:
                    print(f"FAIL: Error upserting to Pinecone namespace {ns_name}: {e}")
                    sys.exit(1)

            offset += batch_size

    if not dry_run:
        print("\nWaiting for Pinecone index to reflect changes...")
        time.sleep(10) # Give Pinecone serverless a moment to ingest

        try:
            stats = index.describe_index_stats()
            pinecone_namespaces = stats.get("namespaces", {})
            for ns_name in namespace_reports:
                ns_stats = pinecone_namespaces.get(ns_name, {})
                namespace_reports[ns_name]["pinecone"] = ns_stats.get("vector_count", 0)
        except Exception as e:
            print(f"Error fetching Pinecone stats: {e}")

    print("\n==================================================")
    print("MIGRATION REPORT")
    print(f"Raw Chroma records: {total_vectors}")
    print(f"Migrated:           {total_valid}")
    print(f"Skipped:            {total_skipped}")
    print("\nNAMESPACE-BY-NAMESPACE REPORT")
    print(f"{'Collection/Namespace':<30} | {'Chroma Raw':<12} | {'Valid':<10} | {'Skipped':<10} | {'Pinecone Count':<15}")
    print("-" * 88)
    for ns_name, rep in namespace_reports.items():
        print(f"{ns_name:<30} | {rep['raw']:<12} | {rep['valid']:<10} | {rep['skipped']:<10} | {rep['pinecone']:<15}")

    print("\nVALIDATION")
    sum_valid = sum(r['valid'] for r in namespace_reports.values())
    print(f"sum(valid counts) == {sum_valid}")
    if sum_valid == total_valid:
        print("Valid sums match.")
    else:
        print("FAIL: sum(valid counts) mismatch!")

    if not dry_run:
        mismatch_found = False
        for ns_name, rep in namespace_reports.items():
            if rep["valid"] != rep["pinecone"]:
                print(f"WARNING: Pinecone count mismatch for {ns_name}: Expected {rep['valid']}, got {rep['pinecone']}")
                mismatch_found = True
        if not mismatch_found:
            print("All Pinecone namespace counts exactly match corresponding valid Chroma counts.")

        print("\nVerifying samples from Pinecone:")
        for ns_name, vid in list(verification_samples.items())[:3]: # check 3 samples
            try:
                fetch_res = index.fetch(ids=[vid], namespace=ns_name)
                vec = fetch_res.get("vectors", {}).get(vid)
                if not vec:
                    print(f"FAIL: Sample verification failed. Could not fetch {vid} from {ns_name}")
                else:
                    dim_ok = len(vec["values"]) == 384
                    text_ok = "text" in vec["metadata"]
                    print(f" - {ns_name}/{vid}: Fetched OK. Dim 384: {dim_ok}. Has text metadata: {text_ok}")
            except Exception as e:
                print(f"Error fetching sample {vid} from {ns_name}: {e}")

    print("==================================================")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate Chroma vectors to Pinecone")
    parser.add_argument("--dry-run", action="store_true", help="Perform a dry run without connecting to Pinecone")
    args = parser.parse_args()

    run_migration(dry_run=args.dry_run)
