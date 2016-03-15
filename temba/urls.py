from __future__ import unicode_literals

import importlib
import logging

from celery.signals import worker_process_init
from django.conf.urls import patterns, include, url
from django.contrib.auth.models import User, AnonymousUser
from django.conf import settings
from temba.channels.views import register, sync

# javascript translation packages
js_info_dict = {
    'packages': (),  # this is empty due to the fact that all translation are in one folder
}

urlpatterns = patterns('',
    url(r'^', include('temba.public.urls')),
    url(r'^', include('temba.msgs.urls')),
    url(r'^', include('temba.contacts.urls')),
    url(r'^', include('temba.orgs.urls')),
    url(r'^', include('temba.schedules.urls')),
    url(r'^', include('temba.flows.urls')),
    url(r'^', include('temba.reports.urls')),
    url(r'^', include('temba.triggers.urls')),
    url(r'^', include('temba.campaigns.urls')),
    url(r'^', include('temba.ivr.urls')),
    url(r'^', include('temba.locations.urls')),
    url(r'^', include('temba.api.urls')),
    url(r'^', include('temba.channels.urls')),
    url(r'^relayers/relayer/sync/(\d+)/$', sync, {}, 'sync'),
    url(r'^relayers/relayer/register/$', register, {}, 'register'),
    url(r'^users/', include('smartmin.users.urls')),
    url(r'^imports/', include('smartmin.csv_imports.urls')),
    url(r'^assets/', include('temba.assets.urls')),
    url(r'^jsi18n/$', 'django.views.i18n.javascript_catalog', js_info_dict)
)

if settings.DEBUG:
    urlpatterns += patterns('', url(r'^media/(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.MEDIA_ROOT, }), )


# import any additional urls
for app in settings.APP_URLS:
    importlib.import_module(app)


# provide a utility method to initialize our analytics
def init_analytics():
    import analytics
    analytics_key = getattr(settings, 'SEGMENT_IO_KEY', None)
    if analytics_key:
        analytics.init(analytics_key, send=settings.IS_PROD, log=not settings.IS_PROD, log_level=logging.DEBUG)

    from temba.utils.analytics import init_librato
    librato_user = getattr(settings, 'LIBRATO_USER', None)
    librato_token = getattr(settings, 'LIBRATO_TOKEN', None)
    if librato_user and librato_token:
        init_librato(librato_user, librato_token)

# initialize our analytics (the signal below will initialize each worker)
init_analytics()


@worker_process_init.connect
def configure_workers(sender=None, **kwargs):
    init_analytics()


def track_user(self):  # pragma: no cover
    """
    Should the current user be tracked
    """

    # don't track unless we are on production
    if not settings.IS_PROD:
        return False

    # always track them if they haven't logged in
    if not self.is_authenticated() or self.is_anonymous():
        return True

    # never track nyaruka email accounts
    if 'nyaruka' in self.email:
        return False

    # never track nyaruka org
    org = self.get_org()
    if org and org.name and 'nyaruka' in org.name.lower():
        return False

    return True

User.track_user = track_user
AnonymousUser.track_user = track_user


def handler500(request):
    """
    500 error handler which includes ``request`` in the context.

    Templates: `500.html`
    Context: None
    """
    from django.template import Context, loader
    from django.http import HttpResponseServerError

    t = loader.get_template('500.html')
    return HttpResponseServerError(t.render(Context({
        'request': request,
    })))
