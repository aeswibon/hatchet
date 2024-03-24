import datetime
import json

import grpc
from google.protobuf import timestamp_pb2

from ..events_pb2 import PushEventRequest, PutLogRequest
from ..events_pb2_grpc import EventsServiceStub
from ..loader import ClientConfig
from ..metadata import get_metadata


def new_event(conn, config: ClientConfig):
    return EventClientImpl(
        client=EventsServiceStub(conn),
        token=config.token,
        namespace=config.namespace or "",
    )


def proto_timestamp_now():
    t = datetime.datetime.now().timestamp()
    seconds = int(t)
    nanos = int(t % 1 * 1e9)

    return timestamp_pb2.Timestamp(seconds=seconds, nanos=nanos)


class EventClientImpl:
    def __init__(self, client, token, namespace):
        self.client = client
        self.token = token
        self.namespace = namespace

    def push(self, event_key, payload):
        try:
            payload_bytes = json.dumps(payload).encode("utf-8")
        except json.UnicodeEncodeError as e:
            raise ValueError(f"Error encoding payload: {e}")

        event_key = f"{self.namespace}:{event_key}"
        request = PushEventRequest(
            key=event_key,
            payload=payload_bytes,
            eventTimestamp=proto_timestamp_now(),
        )

        try:
            self.client.Push(request, metadata=get_metadata(self.token))
        except grpc.RpcError as e:
            raise ValueError(f"gRPC error: {e}")

    def log(self, message: str, step_run_id: str):
        try:
            request = PutLogRequest(
                stepRunId=step_run_id,
                createdAt=proto_timestamp_now(),
                message=message,
            )

            self.client.PutLog(request, metadata=get_metadata(self.token))
        except Exception as e:
            raise ValueError(f"Error logging: {e}")
