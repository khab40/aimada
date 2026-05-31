def build_incident_report(incident: dict[str, object]) -> str:
    title = incident.get("title", "Synthetic incident")
    confidence = incident.get("confidence", "unknown")
    return f"# {title}\n\nConfidence: {confidence}\n"
