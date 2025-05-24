from django.test import TestCase

# Create your tests here.
import pytest
from channels.layers import get_channel_layer
from asgiref.testing import ApplicationCommunicator
import asyncio


@pytest.mark.asyncio
async def test_channel_layer_send_and_receive():
    channel_layer = get_channel_layer()
    print(channel_layer)
    # Send a message to a channel
    await channel_layer.send(
        "test-channel", {"type": "test.message", "text": "Hello, world!"}
    )

    # Receive the message
    message = await channel_layer.receive("test-channel")
    print(message)
    assert message["type"] == "test.message"
    assert message["text"] == "Hello, world!"
