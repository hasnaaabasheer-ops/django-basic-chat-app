from django.urls import path
from . import views


app_name = 'chat'


urlpatterns = [

    path(
        '',
        views.chat_home,
        name='index'
    ),

    path(
        'user/<int:receiver_id>/',
        views.chat_home,
        name='conversation'
    ),

    # Send / receive
    path(
        'api/send/<int:receiver_id>/',
        views.send_message_api,
        name='api_send'
    ),

    path(
        'api/messages/<int:receiver_id>/',
        views.get_new_messages_api,
        name='api_get_messages'
    ),

    # Edit
    path(
        'api/edit/<int:message_id>/',
        views.edit_message_api,
        name='api_edit'
    ),

    # Delete
    path(
        'api/delete-for-me/<int:message_id>/',
        views.delete_for_me_api,
        name='api_delete_for_me'
    ),

    path(
        'api/delete-for-everyone/<int:message_id>/',
        views.delete_for_everyone_api,
        name='api_delete_for_everyone'
    ),

    # Pin / Keep
    path(
        'api/pin/<int:message_id>/',
        views.pin_message_api,
        name='api_pin'
    ),

    path(
        'api/keep/<int:message_id>/',
        views.keep_message_api,
        name='api_keep'
    ),

    # Reply / Forward
    path(
        'api/reply/<int:message_id>/',
        views.reply_message_api,
        name='api_reply'
    ),

    path(
        'api/forward/<int:message_id>/',
        views.forward_message_api,
        name='api_forward'
    ),

]
