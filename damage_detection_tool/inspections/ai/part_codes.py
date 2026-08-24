EXTERIOR_PART_CODE_CATALOG = {
    "front_bumper": "A00",
    "rear_bumper": "A60",
    "right_fender": "A2R",
    "left_fender": "A2L",
    "right_quarterpanel": "A15R",
    "left_quarterpanel": "A15L",
    "front_windscreen": "A10F",
    "rear_windscreen": "A10R",
    # Not returned by the model (no quarter-glass class) — mapping only.
    "right_quarter_glass": "A13R",
    "left_quarter_glass": "A13L",
    "bonnet": "A20",
    "roof": "A30",
    "boot": "A40",
    "right_rocker": "A5R",
    "left_rocker": "A5L",
    "right_headlight": "A1R",
    # Not currently returned (headlight damage always resolves to the
    # right code) — mapping only.
    "left_headlight": "A1L",
    "right_taillight": "A17R",
    # Not currently returned (taillight damage always resolves to the
    # right code) — mapping only.
    "left_taillight": "A17L",
    # TODO: sidemirror part codes have not been provided yet.
    "right_sidemirror": "A14R",
    "left_sidemirror": "A14L",
    "right_front_door": "A9R",
    "left_front_door": "A9L",
    # Not currently returned (doorouter-dent always resolves to the
    # front door code, model can't distinguish front/rear) — mapping only.
    "right_rear_door": "A8R",
    "left_rear_door": "A8L",
    # Not returned by the model (no sidewindow class) — mapping only.
    "right_front_sidewindow": "A11R",
    "left_front_sidewindow": "A11L",
    "right_rear_sidewindow": "A12R",
    "left_rear_sidewindow": "A12L",
}


def _side_from_angle(angle_code):

    angle_code = angle_code or ""

    if "right" in angle_code:
        return "right"

    if "left" in angle_code:
        return "left"

    return None


def resolve_exterior_part_code(damage_class, angle_code):
    """
    Resolve the part code for one exterior damage detection.

    damage_class: the raw class string from the FastAPI model
        (e.g. "fender-dent", "Headlight-damage").
    angle_code: the exterior angle the image was captured from
        (e.g. "front", "right", "front_right").
    """

    damage_class = (damage_class or "").strip().lower()

    side = _side_from_angle(angle_code)

    # ---------------------------------------------------------------
    # Windscreen — no side, class tells us front vs rear directly.
    # ---------------------------------------------------------------

    if damage_class == "front-windscreen-damage":
        return EXTERIOR_PART_CODE_CATALOG["front_windscreen"]

    if damage_class == "rear-windscreen-damage":
        return EXTERIOR_PART_CODE_CATALOG["rear_windscreen"]

    # ---------------------------------------------------------------
    # Headlight / sidemirror / taillight — always the right-side code.
    # ---------------------------------------------------------------

    if damage_class == "headlight-damage":
        return EXTERIOR_PART_CODE_CATALOG["right_headlight"]

    if damage_class == "sidemirror-damage":
        return EXTERIOR_PART_CODE_CATALOG["right_sidemirror"] or "UNKNOWN"

    if damage_class == "taillight-damage":
        return EXTERIOR_PART_CODE_CATALOG["right_taillight"]

    # ---------------------------------------------------------------
    # Bonnet / roof / boot — single part, no side.
    # ---------------------------------------------------------------

    if damage_class == "bonnet-dent":
        return EXTERIOR_PART_CODE_CATALOG["bonnet"]

    if damage_class == "roof-dent":
        return EXTERIOR_PART_CODE_CATALOG["roof"]

    if damage_class == "boot-dent":
        return EXTERIOR_PART_CODE_CATALOG["boot"]

    # ---------------------------------------------------------------
    # Bumpers — class tells us front vs rear directly.
    # ---------------------------------------------------------------

    if damage_class == "front-bumper-dent":
        return EXTERIOR_PART_CODE_CATALOG["front_bumper"]

    if damage_class == "rear-bumper-dent":
        return EXTERIOR_PART_CODE_CATALOG["rear_bumper"]

    # ---------------------------------------------------------------
    # Fender / quarterpanel / running board — side comes from the
    # capture angle the damage was detected in.
    # ---------------------------------------------------------------

    if damage_class == "fender-dent":

        if side == "right":
            return EXTERIOR_PART_CODE_CATALOG["right_fender"]

        if side == "left":
            return EXTERIOR_PART_CODE_CATALOG["left_fender"]

        return "UNKNOWN"

    if damage_class == "quaterpanel-dent":

        if side == "right":
            return EXTERIOR_PART_CODE_CATALOG["right_quarterpanel"]

        if side == "left":
            return EXTERIOR_PART_CODE_CATALOG["left_quarterpanel"]

        return "UNKNOWN"

    if damage_class == "runningboard-damage":

        if side == "right":
            return EXTERIOR_PART_CODE_CATALOG["right_rocker"]

        if side == "left":
            return EXTERIOR_PART_CODE_CATALOG["left_rocker"]

        return "UNKNOWN"

    # ---------------------------------------------------------------
    # Door outer — the model can't tell front vs rear door, so this
    # always resolves to the FRONT door code for the capture side.
    # ---------------------------------------------------------------

    if damage_class == "doorouter-dent":

        if side == "right":
            return EXTERIOR_PART_CODE_CATALOG["right_front_door"]

        if side == "left":
            return EXTERIOR_PART_CODE_CATALOG["left_front_door"]

        return "UNKNOWN"

    return "UNKNOWN"
