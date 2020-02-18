import os
import logging
from django.apps.registry import apps
from django.utils.text import slugify
from keycloak.exceptions import KeycloakClientError
import django_keycloak.services.client

logger = logging.getLogger(__name__)

MODELS_FOR_SYNCHRONIZE_RESOURCES = os.getenv('MODELS_FOR_SYNCHRONIZE_RESOURCES')

def synchronize_client(client):
    """
    Synchronize all models as resources for a client.
    :type client: django_keycloak.models.Client
    """
    for app_config in apps.get_app_configs():
        synchronize_resources(
            client=client,
            app_config=app_config
        )


def synchronize_resources(client, app_config):
    """
    Synchronize all resources (models) to the Keycloak server for given client
    and Django App.
    :type client: django_keycloak.models.Client
    :type app_config: django.apps.config.AppConfig
    """
    if not app_config.models_module:
        return
    excepted_models = []

    if MODELS_FOR_SYNCHRONIZE_RESOURCES:
        if app_config.name in MODELS_FOR_SYNCHRONIZE_RESOURCES:
            excepted_models = app_config.models
        else:
            logger.info("App config with name {} doesn't exist".format(app_config.name))
    else:
        excepted_models = app_config.models
    _create_resources(excepted_models, client)


def _create_resources(excepted_models, client):
    """
    :type excepted_models: list of django.db.models.Model
    :type client: django_keycloak.models.Client
    """
    if not excepted_models:
        return
    uma_client = client.uma_api_client()
    access_token = django_keycloak.services.client.get_access_token(
        client=client
    )
    for klass in excepted_models.values():
        scopes = _get_all_permissions(klass._meta)
        try:
            uma_client.resource_set_create(
                token=access_token,
                name=klass._meta.label_lower,
                type='urn:{client}:resources:{model}'.format(
                    client=slugify(client.client_id),
                    model=klass._meta.label_lower
                ),
                scopes=scopes
            )
        except KeycloakClientError as e:
            if e.original_exc.response.status_code != 409:
                raise


def _get_all_permissions(meta):
    """
    :type meta: django.db.models.options.Options
    :rtype: list
    """
    return meta.default_permissions
