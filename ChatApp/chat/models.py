from django.db import models
from django.contrib.auth.models import User


class Message(models.Model):

    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sent_messages'
    )

    receiver = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='received_messages'
    )

    content = models.TextField()

    # Read / Seen
    is_read = models.BooleanField(
        default=False
    )

    seen_at = models.DateTimeField(
        null=True,
        blank=True
    )

    # Edit
    is_edited = models.BooleanField(
        default=False
    )

    edited_at = models.DateTimeField(
        null=True,
        blank=True
    )

    # Reply
    reply_to = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='replies'
    )

    # Forward
    forwarded_from = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='forwards'
    )

    # Delete for everyone
    is_deleted_for_everyone = models.BooleanField(
        default=False
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.sender.username} -> {self.receiver.username}: {self.content[:20]}"


class MessageUserAction(models.Model):
    """
    Stores actions that are specific to a user.

    Example:
    - Hasna deletes a message for herself
    - Hasna keeps a message
    - Hasna pins a message
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='message_actions'
    )

    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name='user_actions'
    )

    # Delete only for this user
    deleted_for_me = models.BooleanField(
        default=False
    )

    # Keep / save message
    is_kept = models.BooleanField(
        default=False
    )

    # Pin message
    is_pinned = models.BooleanField(
        default=False
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'message'],
                name='unique_user_message_action'
            )
        ]

    def __str__(self):
        return f"{self.user.username} - Message {self.message.id}"

