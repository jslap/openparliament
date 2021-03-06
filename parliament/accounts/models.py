from base64 import urlsafe_b64encode
import datetime
import os

from django.core import urlresolvers
from django.core.mail import send_mail
from django.db import models
from django.template import loader, Context

from jsonfield import JSONField


class User(models.Model):

    email = models.EmailField(unique=True, db_index=True)
    email_bouncing = models.BooleanField(default=False)
    email_bounce_reason = models.TextField(blank=True)

    name = models.CharField(max_length=250, blank=True)

    created = models.DateTimeField(default=datetime.datetime.now)
    last_login = models.DateTimeField(blank=True, null=True)

    data = JSONField(default={})

    def __unicode__(self):
        return self.email

    def log_in(self, request):
        request.authenticated_email = self.email
        self.__class__.objects.filter(id=self.id).update(last_login=datetime.datetime.now())

def _random_token():
    return urlsafe_b64encode(os.urandom(15))

class TokenError(Exception):

    def __init__(self, message, email=None):
        super(TokenError, self).__init__(message)
        self.email = email

class LoginToken(models.Model):
    token = models.CharField(max_length=40, primary_key=True,
        default=_random_token)
    email = models.EmailField()
    created = models.DateTimeField(default=datetime.datetime.now)
    requesting_ip = models.GenericIPAddressField()
    used = models.BooleanField(default=False)
    login_ip = models.GenericIPAddressField(blank=True, null=True)
    post_login_url = models.TextField(blank=True)

    MAX_TOKEN_AGE = datetime.timedelta(seconds=60*60)

    def __unicode__(self):
        return "%s for %s" % (self.token, self.email)

    @classmethod
    def generate(cls, email, requesting_ip):
        lt = cls.objects.create(email=email, requesting_ip=requesting_ip)
        login_url = urlresolvers.reverse('token_login', kwargs={'token': lt.token})
        ctx = Context({'login_url': login_url})
        t = loader.get_template("accounts/token_login.txt")
        send_mail(subject=u'Log in to openparliament.ca',
            message=t.render(ctx),
            from_email='alerts@contact.openparliament.ca',
            recipient_list=[email])
        return lt

    @classmethod
    def validate(cls, token, login_ip):
        try:
            lt = cls.objects.get(token=token)
        except cls.DoesNotExist:
            raise TokenError("That login code couldn't be found. Try cutting and pasting it directly "
                "from your email to your browser's address bar.")

        if lt.used:
            raise TokenError("That login code has already been used. You can request another login email on this page.",
                email=lt.email)

        if (datetime.datetime.now() - lt.created) > cls.MAX_TOKEN_AGE:
            raise TokenError("That login code has expired. Please enter your email again, then click the link within an hour.", email=lt.email)

        lt.login_ip = login_ip
        lt.used = True
        lt.save()
        return lt
