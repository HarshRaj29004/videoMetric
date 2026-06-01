import logging

logging.basicConfig(level=logging.INFO)


def reset_vector_db(INDEX, ids: list, metadatas: list, namespace: str = "videometric"):
    if not INDEX:
        logging.warning("Pinecone index not configured; nothing to reset.")
        return {"deleted": False, "namespace": namespace, "reason": "pinecone_not_configured"}

    try:
        INDEX.delete(delete_all=True, namespace=namespace)
        ids.clear()
        metadatas.clear()
        logging.info("Cleared Pinecone namespace %s", namespace)
        return {"deleted": True, "namespace": namespace}
    except Exception as e:
        error_name = e.__class__.__name__
        error_text = str(e)

        if error_name == "NotFoundError" or "Namespace not found" in error_text or "[404]" in error_text:
            ids.clear()
            metadatas.clear()
            logging.warning("Pinecone namespace %s was already absent", namespace)
            return {"deleted": True, "namespace": namespace, "already_empty": True}

        logging.exception("Failed to clear Pinecone namespace %s: %s", namespace, e)
        return {"deleted": False, "namespace": namespace, "error": str(e)}