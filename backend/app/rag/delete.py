import logging
from ..core.pinecone_client import INDEX, NAMESPACE

logging.basicConfig(level=logging.INFO)


def reset_vector_db(ids: list, metadatas: list):
    if not INDEX:
        logging.warning("Pinecone index not configured; nothing to reset.")
        return {"deleted": False, "NAMESPACE": NAMESPACE, "reason": "pinecone_not_configured"}

    try:
        INDEX.delete(delete_all=True, namespace=NAMESPACE)
        ids.clear()
        metadatas.clear()
        logging.info("Cleared Pinecone namespace %s", NAMESPACE)
        return {"deleted": True, "namespace": NAMESPACE}
    except Exception as e:
        error_name = e.__class__.__name__
        error_text = str(e)

        if error_name == "NotFoundError" or "NAMESPACE not found" in error_text or "[404]" in error_text:
            ids.clear()
            metadatas.clear()
            logging.warning("Pinecone namespace %s was already absent", NAMESPACE)
            return {"deleted": True, "namespace": NAMESPACE, "already_empty": True}

        logging.exception("Failed to clear Pinecone namespace %s: %s", NAMESPACE, e)
        return {"deleted": False, "namespace": NAMESPACE, "error": str(e)}