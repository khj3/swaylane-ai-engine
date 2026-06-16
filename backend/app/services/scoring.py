def calculate_ai_readiness(submission: dict) -> int:
    score = 0
    checks = [
        (submission.get("tryon_image_url") or _has_image_type(submission, "main"), 15, "Main image"),
        (_has_image_type(submission, "front"), 10, "Front image"),
        (_has_image_type(submission, "back"), 10, "Back image"),
        (_has_image_type(submission, "model"), 10, "Model image"),
        (bool(submission.get("material_composition")), 10, "Material composition"),
        (bool(submission.get("fit_type")), 10, "Fit type"),
        (_has_measurements(submission), 15, "Garment measurements"),
        (bool(submission.get("garment_type")), 10, "Garment type"),
        (bool(submission.get("prompt_guidance")), 5, "Prompt guidance"),
        (submission.get("garment_type") in ("top", "bottom", "full_outfit", "outerwear"), 5, "Try-on compatible"),
    ]
    for passed, points, _label in checks:
        if passed:
            score += points
    return min(100, score)


def calculate_rack_readiness(submission: dict) -> int:
    score = 0
    checks = [
        (bool(submission.get("layer_category")), 20, "Layer category"),
        (submission.get("can_layer") is not None, 10, "Can layer"),
        (bool(submission.get("recommended_pairings")), 15, "Recommended pairings"),
        (bool(submission.get("conflicting_categories")), 10, "Conflicting categories"),
        (bool(submission.get("styling_notes")), 15, "Styling notes"),
        (bool(submission.get("outfit_prompt_guidance")), 10, "Outfit prompt guidance"),
        (bool(submission.get("category")), 10, "Product category"),
        (_has_image_type(submission, "main"), 5, "Has image"),
        (bool(submission.get("garment_type")), 5, "Garment type"),
    ]
    for passed, points, _label in checks:
        if passed:
            score += points
    return min(100, score)


def readiness_label(score: int) -> str:
    if score >= 90:
        return "Best AI Ready"  # or "Best Rack Ready"
    if score >= 70:
        return "Ready"
    if score >= 40:
        return "Partially Ready"
    return "Not Ready"


def readiness_color(label: str) -> str:
    return {"Best AI Ready": "green", "Ready": "green", "Partially Ready": "orange", "Not Ready": "red"}.get(label, "gray")


def missing_items_ai(submission: dict) -> list:
    missing = []
    if not submission.get("tryon_image_url") and not _has_image_type(submission, "main"):
        missing.append("Add a main product image")
    if not _has_image_type(submission, "front"):
        missing.append("Add a front image")
    if not _has_image_type(submission, "back"):
        missing.append("Add a back image to improve AI readiness")
    if not submission.get("material_composition"):
        missing.append("Add material composition details")
    if not submission.get("fit_type"):
        missing.append("Add fit type")
    if not _has_measurements(submission):
        missing.append("Add garment measurements to improve fit confidence")
    if not submission.get("garment_type"):
        missing.append("Add garment type")
    return missing


def missing_items_rack(submission: dict) -> list:
    missing = []
    if not submission.get("layer_category"):
        missing.append("Add layer category so this can be used in full outfits")
    if not submission.get("recommended_pairings"):
        missing.append("Add recommended pairings to improve outfit suggestions")
    if not submission.get("styling_notes"):
        missing.append("Add styling notes to improve AI full-fit generation")
    if not submission.get("outfit_prompt_guidance"):
        missing.append("Add outfit prompt guidance")
    return missing


def _has_image_type(submission: dict, img_type: str) -> bool:
    images = submission.get("images", [])
    if isinstance(images, list):
        return any(i.get("image_type") == img_type for i in images)
    return False


def _has_measurements(submission: dict) -> bool:
    measurements = submission.get("measurements", [])
    if isinstance(measurements, list):
        return len(measurements) > 0
    return bool(submission.get("chest_width") or submission.get("waist") or submission.get("hips"))
