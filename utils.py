from django.apps import apps

def get_user_model():
    return apps.get_model('accounts', 'CustomUser')

APPLICATIONS_USER_MODEL = get_user_model()

def get_token_user(token):
    try:
        token_user = AuthToken.objects.get(token_key=token[:8])  # Knox uses first 8 chars
    except ObjectDoesNotExist:
        return "Invalid Token"
    else:
        UserModel = get_user_model()
        return UserModel.objects.get(pk=token_user.user_id)