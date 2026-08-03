def iou(boxA, boxB):

    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])

    inter = max(0, xB-xA) * max(0, yB-yA)

    if inter == 0:
        return 0

    areaA = (boxA[2]-boxA[0])*(boxA[3]-boxA[1])
    areaB = (boxB[2]-boxB[0])*(boxB[3]-boxB[1])

    return inter / float(areaA + areaB - inter)


def compare_damage(before, after):

    new_damage = []

    for damage_after in after:

        found = False

        for damage_before in before:

            if damage_after["type"] != damage_before["type"]:
                continue

            if iou(
                damage_after["bbox"],
                damage_before["bbox"]
            ) > 0.5:

                found = True
                break

        if not found:
            new_damage.append(damage_after)

    return new_damage