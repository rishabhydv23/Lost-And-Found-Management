from datetime import timedelta
from rapidfuzz.fuzz import ratio
from .models import PotentialMatch
from notifications.models import Notification


def calculate_match_score(lost, found):
    category_score = 100 if lost.category_id == found.category_id else 0
    name_score = ratio(lost.item_name, found.item_name)
    color_score = ratio(lost.color, found.color)
    location_score = 100 if lost.campus_location_id == found.campus_location_id else (
        ratio(str(lost.campus_location), str(found.campus_location))
    )
    day_difference = abs((lost.date_occurrence - found.date_occurrence).days)
    date_score = 100 if day_difference == 0 else max(0, 100 - day_difference * 10)
    description_score = ratio(lost.description, found.description)
    return round(
        category_score * 0.25 +
        name_score * 0.15 +
        color_score * 0.15 +
        location_score * 0.20 +
        date_score * 0.15 +
        description_score * 0.10
    )


def run_matching(report):
    if report.status != 'APPROVED':
        return []
    opposite_type = 'FOUND' if report.report_type == 'LOST' else 'LOST'
    candidates = report.__class__.objects.filter(
        report_type=opposite_type,
        status='APPROVED',
    ).exclude(user=report.user)
    matches = []
    if report.report_type == 'LOST':
        lost, founds = report, candidates
    else:
        lost, founds = None, []
    for found in candidates if report.report_type == 'LOST' else candidates:
        if report.report_type == 'LOST':
            lost_report, found_report = report, found
        else:
            lost_report, found_report = found, report
        score = calculate_match_score(lost_report, found_report)
        if score >= 60:
            match, created = PotentialMatch.objects.get_or_create(
                lost_report=lost_report,
                found_report=found_report,
                defaults={'score': score},
            )
            if not created and match.score != score:
                match.score = score
                match.save(update_fields=['score'])
            matches.append(match)
            Notification.objects.get_or_create(
                recipient=lost_report.user,
                notification_type='MATCH',
                message=f"Potential match found: {found_report.item_name} ({score}% score)",
            )
    return matches
