from django.core import signing


SURVEY_TOKEN_SALT = "survey-share"


def make_survey_token(survey_pk: int) -> str:
    return signing.dumps(int(survey_pk), salt=SURVEY_TOKEN_SALT)


def parse_survey_token(token: str) -> int:
    return int(signing.loads(token, salt=SURVEY_TOKEN_SALT, max_age=None))


