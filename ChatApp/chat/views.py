import json

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.db.models import Q, Count
from django.utils import timezone

from .models import Message, MessageUserAction


@login_required
def chat_home(request, receiver_id=None):

    current_user = request.user

    # Get all other users and their unread message counts
    other_users = User.objects.exclude(
        id=current_user.id
    ).annotate(
        unread_count=Count(
            'sent_messages',
            filter=Q(
                sent_messages__receiver=current_user,
                sent_messages__is_read=False
            )
        )
    )

    active_partner = None
    messages_list = []

    if receiver_id:

        active_partner = get_object_or_404(
            User,
            id=receiver_id
        )

        if active_partner == current_user:
            return redirect('chat:index')

        # Mark incoming messages as read and seen
        incoming_messages = Message.objects.filter(
            sender=active_partner,
            receiver=current_user,
            is_read=False
        )

        incoming_messages.update(
            is_read=True,
            seen_at=timezone.now()
        )

        # Get conversation
        messages_list = Message.objects.filter(
            (
                Q(
                    sender=current_user,
                    receiver=active_partner
                )
            )
            |
            (
                Q(
                    sender=active_partner,
                    receiver=current_user
                )
            )
        ).order_by(
            'created_at'
        )

        # Hide messages deleted only for this user
        deleted_ids = MessageUserAction.objects.filter(
            user=current_user,
            message__in=messages_list,
            deleted_for_me=True
        ).values_list(
            'message_id',
            flat=True
        )

        messages_list = messages_list.exclude(
            id__in=deleted_ids
        )

    return render(
        request,
        'chat/chat_room.html',
        {
            'other_users': other_users,
            'active_partner': active_partner,
            'messages_list': messages_list
        }
    )


@login_required
def send_message_api(request, receiver_id):

    if request.method != 'POST':
        return HttpResponseBadRequest(
            "Invalid request method"
        )

    receiver = get_object_or_404(
        User,
        id=receiver_id
    )

    if receiver == request.user:
        return HttpResponseForbidden(
            "Cannot message yourself"
        )

    try:

        data = json.loads(request.body)

        content = data.get(
            'content',
            ''
        ).strip()

    except json.JSONDecodeError:

        return HttpResponseBadRequest(
            "Malformed JSON payload"
        )

    if not content:

        return JsonResponse(
            {
                'status': 'error',
                'message': 'Message cannot be empty'
            },
            status=400
        )

    msg = Message.objects.create(
        sender=request.user,
        receiver=receiver,
        content=content
    )

    return JsonResponse(
        {
            'status': 'success',
            'id': msg.id,
            'content': msg.content,
            'sender': msg.sender.username,
            'timestamp': msg.created_at.strftime('%H:%M'),
            'is_me': True,
            'is_read': False,
            'seen_at': None,
            'is_edited': False
        }
    )


@login_required
def get_new_messages_api(request, receiver_id):

    active_partner = get_object_or_404(
        User,
        id=receiver_id
    )

    last_id = request.GET.get(
        'last_id',
        0
    )

    new_messages = Message.objects.filter(
        (
            Q(
                sender=request.user,
                receiver=active_partner
            )
            |
            Q(
                sender=active_partner,
                receiver=request.user
            )
        ),
        id__gt=last_id
    ).order_by(
        'created_at'
    )

    # Mark incoming messages as read and seen
    incoming_messages = Message.objects.filter(
        sender=active_partner,
        receiver=request.user,
        is_read=False
    )

    incoming_messages.update(
        is_read=True,
        seen_at=timezone.now()
    )

    data = []

    for message in new_messages:

        if MessageUserAction.objects.filter(
            user=request.user,
            message=message,
            deleted_for_me=True
        ).exists():

            continue

        data.append(
            {
                'id': message.id,
                'sender': message.sender.username,
                'content': (
                    'This message was deleted'
                    if message.is_deleted_for_everyone
                    else message.content
                ),
                'timestamp': message.created_at.strftime('%H:%M'),
                'is_me': message.sender == request.user,
                'is_read': message.is_read,
                'seen_at': (
                    message.seen_at.isoformat()
                    if message.seen_at
                    else None
                ),
                'is_edited': message.is_edited,
                'is_deleted_for_everyone':
                    message.is_deleted_for_everyone
            }
        )

    return JsonResponse(
        {
            'messages': data
        }
    )


# =========================================================
# EDIT MESSAGE
# =========================================================

@login_required
def edit_message_api(request, message_id):

    if request.method != 'POST':
        return HttpResponseBadRequest(
            "Invalid request method"
        )

    message = get_object_or_404(
        Message,
        id=message_id
    )

    if message.sender != request.user:
        return HttpResponseForbidden(
            "You can only edit your own messages"
        )

    if message.is_deleted_for_everyone:
        return JsonResponse(
            {
                'status': 'error',
                'message': 'Deleted messages cannot be edited'
            },
            status=400
        )

    try:

        data = json.loads(request.body)

        content = data.get(
            'content',
            ''
        ).strip()

    except json.JSONDecodeError:

        return HttpResponseBadRequest(
            "Malformed JSON payload"
        )

    if not content:

        return JsonResponse(
            {
                'status': 'error',
                'message': 'Message cannot be empty'
            },
            status=400
        )

    message.content = content
    message.is_edited = True
    message.edited_at = timezone.now()

    message.save(
        update_fields=[
            'content',
            'is_edited',
            'edited_at'
        ]
    )

    return JsonResponse(
        {
            'status': 'success',
            'id': message.id,
            'content': message.content,
            'is_edited': True
        }
    )


# =========================================================
# DELETE FOR ME
# =========================================================

@login_required
def delete_for_me_api(request, message_id):

    if request.method != 'POST':
        return HttpResponseBadRequest(
            "Invalid request method"
        )

    message = get_object_or_404(
        Message,
        id=message_id
    )

    MessageUserAction.objects.update_or_create(
        user=request.user,
        message=message,
        defaults={
            'deleted_for_me': True
        }
    )

    return JsonResponse(
        {
            'status': 'success',
            'message': 'Message deleted for you'
        }
    )


# =========================================================
# DELETE FOR EVERYONE
# =========================================================

@login_required
def delete_for_everyone_api(request, message_id):

    if request.method != 'POST':
        return HttpResponseBadRequest(
            "Invalid request method"
        )

    message = get_object_or_404(
        Message,
        id=message_id
    )

    if message.sender != request.user:
        return HttpResponseForbidden(
            "You can only delete your own messages for everyone"
        )

    message.is_deleted_for_everyone = True
    message.content = 'This message was deleted'

    message.save(
        update_fields=[
            'content',
            'is_deleted_for_everyone'
        ]
    )

    return JsonResponse(
        {
            'status': 'success',
            'message': 'Message deleted for everyone'
        }
    )


# =========================================================
# PIN MESSAGE
# =========================================================

@login_required
def pin_message_api(request, message_id):

    if request.method != 'POST':
        return HttpResponseBadRequest(
            "Invalid request method"
        )

    message = get_object_or_404(
        Message,
        id=message_id
    )

    action, created = MessageUserAction.objects.get_or_create(
        user=request.user,
        message=message
    )

    action.is_pinned = not action.is_pinned

    action.save(
        update_fields=['is_pinned']
    )

    return JsonResponse(
        {
            'status': 'success',
            'is_pinned': action.is_pinned
        }
    )


# =========================================================
# KEEP MESSAGE
# =========================================================

@login_required
def keep_message_api(request, message_id):

    if request.method != 'POST':
        return HttpResponseBadRequest(
            "Invalid request method"
        )

    message = get_object_or_404(
        Message,
        id=message_id
    )

    action, created = MessageUserAction.objects.get_or_create(
        user=request.user,
        message=message
    )

    action.is_kept = not action.is_kept

    action.save(
        update_fields=['is_kept']
    )

    return JsonResponse(
        {
            'status': 'success',
            'is_kept': action.is_kept
        }
    )


# =========================================================
# REPLY
# =========================================================

@login_required
def reply_message_api(request, message_id):

    if request.method != 'POST':
        return HttpResponseBadRequest(
            "Invalid request method"
        )

    original_message = get_object_or_404(
        Message,
        id=message_id
    )

    if original_message.sender != request.user and \
       original_message.receiver != request.user:

        return HttpResponseForbidden(
            "You cannot reply to this message"
        )

    try:

        data = json.loads(request.body)

        content = data.get(
            'content',
            ''
        ).strip()

    except json.JSONDecodeError:

        return HttpResponseBadRequest(
            "Malformed JSON payload"
        )

    if not content:

        return JsonResponse(
            {
                'status': 'error',
                'message': 'Reply cannot be empty'
            },
            status=400
        )

    receiver = (
        original_message.receiver
        if original_message.sender == request.user
        else original_message.sender
    )

    message = Message.objects.create(
        sender=request.user,
        receiver=receiver,
        content=content,
        reply_to=original_message
    )

    return JsonResponse(
        {
            'status': 'success',
            'id': message.id,
            'content': message.content,
            'timestamp': message.created_at.strftime('%H:%M'),
            'is_me': True,
            'reply_to': original_message.content
        }
    )


# =========================================================
# FORWARD
# =========================================================

@login_required
def forward_message_api(request, message_id):

    if request.method != 'POST':
        return HttpResponseBadRequest(
            "Invalid request method"
        )

    original_message = get_object_or_404(
        Message,
        id=message_id
    )

    try:

        data = json.loads(request.body)

        receiver_id = data.get(
            'receiver_id'
        )

    except json.JSONDecodeError:

        return HttpResponseBadRequest(
            "Malformed JSON payload"
        )

    receiver = get_object_or_404(
        User,
        id=receiver_id
    )

    if receiver == request.user:
        return HttpResponseForbidden(
            "Cannot forward to yourself"
        )

    message = Message.objects.create(
        sender=request.user,
        receiver=receiver,
        content=original_message.content,
        forwarded_from=original_message
    )

    return JsonResponse(
        {
            'status': 'success',
            'id': message.id,
            'content': message.content,
            'timestamp': message.created_at.strftime('%H:%M'),
            'is_me': True,
            'forwarded': True
        }
    )
