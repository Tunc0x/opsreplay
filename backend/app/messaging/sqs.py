import json
import os
from typing import Any, Protocol

import boto3


class SQSConfigurationError(RuntimeError):
    """Required SQS publisher configuration is missing or invalid."""


class SQSClient(Protocol):
    def get_queue_url(self, *, QueueName: str) -> dict[str, Any]: ...

    def send_message(
        self,
        *,
        QueueUrl: str,
        MessageBody: str,
    ) -> dict[str, Any]: ...

    def receive_message(
        self,
        *,
        QueueUrl: str,
        MaxNumberOfMessages: int,
        WaitTimeSeconds: int,
    ) -> dict[str, Any]: ...

    def delete_message(
        self,
        *,
        QueueUrl: str,
        ReceiptHandle: str,
    ) -> dict[str, Any]: ...


def create_sqs_client() -> SQSClient:
    region = os.getenv("AWS_REGION")
    if not region:
        raise SQSConfigurationError("AWS_REGION is required.")

    client_options = {"region_name": region}
    endpoint_url = os.getenv("SQS_ENDPOINT_URL")
    if endpoint_url:
        client_options["endpoint_url"] = endpoint_url

    return boto3.client("sqs", **client_options)


def get_webhook_queue_name() -> str:
    queue_name = os.getenv("SQS_WEBHOOK_QUEUE_NAME")
    if not queue_name:
        raise SQSConfigurationError("SQS_WEBHOOK_QUEUE_NAME is required.")
    return queue_name


def resolve_webhook_queue_url(
    sqs_client: SQSClient,
    queue_name: str,
) -> str:
    response = sqs_client.get_queue_url(QueueName=queue_name)
    queue_url = response.get("QueueUrl")
    if not isinstance(queue_url, str) or not queue_url:
        raise RuntimeError("SQS returned an invalid queue URL.")
    return queue_url

# send to SQS
def publish_webhook_delivery_reference(
    sqs_client: SQSClient,
    queue_url: str,
    webhook_delivery_id: int,
) -> None:
    message_body = json.dumps(
        {"webhook_delivery_id": webhook_delivery_id}
    )
    sqs_client.send_message(
        QueueUrl=queue_url,
        MessageBody=message_body,
    )


def receive_webhook_message(
    sqs_client: SQSClient,
    queue_url: str,
) -> dict[str, Any] | None:
    # If the queue is empty, keep this receive request open for up to
    # 10 seconds. If no message arrives, return no message.
    response = sqs_client.receive_message(
        QueueUrl=queue_url,
        MaxNumberOfMessages=1,
        WaitTimeSeconds=10,
    )
    messages = response.get("Messages")
    if messages is None or messages == []:
        return None
    if not isinstance(messages, list) or not isinstance(messages[0], dict):
        raise RuntimeError("SQS returned malformed message data.")
    return messages[0]


def delete_webhook_message(
    sqs_client: SQSClient,
    queue_url: str,
    receipt_handle: str,
) -> None:
    sqs_client.delete_message(
        QueueUrl=queue_url,
        ReceiptHandle=receipt_handle,
    )
