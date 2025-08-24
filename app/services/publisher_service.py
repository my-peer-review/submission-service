import asyncio
import json
import logging
from datetime import datetime
from typing import Optional

import aio_pika
from aio_pika import Message, DeliveryMode, ExchangeType
from aio_pika.abc import (
    AbstractRobustConnection, AbstractRobustChannel, AbstractExchange
)

logger = logging.getLogger(__name__)


class SubmissionPublisher:
    """
    Publisher per notificare eventi submission sia al dominio "review"
    sia al dominio "report".

    - exchange review (esistente):   direct "elearning.submission-review", rk "submission.review"
    - exchange report (nuovo):       direct "elearning.reports",          rk "submissions.reports"
    """

    def __init__(
        self,
        rabbitmq_url: str,
        heartbeat: int,
        *,
        review_exchange: str = "elearning.submissions-consegnate",
        review_routing_key: str = "submissions.reviews",
        report_exchange: str = "elearning.reports",
        report_routing_key: str = "submissions.reports",
    ) -> None:
        self.rabbitmq_url = rabbitmq_url
        self.heartbeat = heartbeat

        # review
        self.review_exchange_name = review_exchange
        self.review_routing_key = review_routing_key

        # report (NUOVO)
        self.report_exchange_name = report_exchange
        self.report_routing_key = report_routing_key

        # risorse AMQP
        self._conn: Optional[AbstractRobustConnection] = None
        self._channel: Optional[AbstractRobustChannel] = None
        self._review_exchange: Optional[AbstractExchange] = None
        self._report_exchange: Optional[AbstractExchange] = None

        self._lock = asyncio.Lock()

    # -------------------------
    # Connessione & lifecycle
    # -------------------------
    async def connect(self, max_retries: int = 5, delay: int = 3) -> None:
        attempt = 0
        while True:
            try:
                logger.debug("Tentativo connessione RabbitMQ #%s", attempt + 1)
                self._conn = await aio_pika.connect_robust(self.rabbitmq_url, heartbeat=self.heartbeat)
                self._channel = await self._conn.channel(publisher_confirms=True)
                await self._channel.set_qos(prefetch_count=10)

                # dichiara entrambi gli exchange (direct, durevoli)
                self._review_exchange = await self._channel.declare_exchange(
                    self.review_exchange_name, ExchangeType.DIRECT, durable=True
                )
                self._report_exchange = await self._channel.declare_exchange(
                    self.report_exchange_name, ExchangeType.DIRECT, durable=True
                )

                logger.info("Connessione a RabbitMQ stabilita e exchange dichiarati.")
                return
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                attempt += 1
                logger.warning("Connessione fallita: %s", exc)
                if attempt >= max_retries:
                    logger.error("Impossibile connettersi a RabbitMQ dopo %s tentativi.", max_retries)
                    raise
                await asyncio.sleep(delay)

    async def close(self) -> None:
        async with self._lock:
            try:
                if self._channel and not self._channel.is_closed:
                    await self._channel.close()
            finally:
                if self._conn and not self._conn.is_closed:
                    await self._conn.close()
            self._conn = None
            self._channel = None
            self._review_exchange = None
            self._report_exchange = None

    async def _ensure_ready(self) -> None:
        if not self._conn or self._conn.is_closed:
            await self.connect()
        if not self._channel or self._channel.is_closed:
            assert self._conn is not None
            self._channel = await self._conn.channel(publisher_confirms=True)
            await self._channel.set_qos(prefetch_count=10)
        if not self._review_exchange:
            assert self._channel is not None
            self._review_exchange = await self._channel.declare_exchange(
                self.review_exchange_name, ExchangeType.DIRECT, durable=True
            )
        if not self._report_exchange:
            assert self._channel is not None
            self._report_exchange = await self._channel.declare_exchange(
                self.report_exchange_name, ExchangeType.DIRECT, durable=True
            )

    # -------------------------
    # Publish helpers
    # -------------------------
    @staticmethod
    def _build_submission_payload(
        assignmentId: str,
        submissionId: str,
        studentId: str,
        deliveredAt: datetime,
    ) -> dict:
        return {
            "assignmentId": assignmentId,
            "submissionId": submissionId,
            "studentId": studentId,
            "deliveredAt": deliveredAt.isoformat(),
        }

    # -------------------------
    # Publish: REVIEW
    # -------------------------
    async def publish_submission_delivered(
        self,
        assignmentId: str,
        submissionId: str,
        studentId: str,
        deliveredAt: datetime,
    ) -> None:
        """Invia il messaggio al dominio REVIEW."""
        await self._ensure_ready()
        assert self._review_exchange is not None

        payload = self._build_submission_payload(assignmentId, submissionId, studentId, deliveredAt)
        body = json.dumps(payload).encode("utf-8")
        msg = Message(
            body=body,
            content_type="application/json",
            delivery_mode=DeliveryMode.NOT_PERSISTENT,
            headers={"eventType": "submission.delivered"},
        )

        logger.debug(
            "Publishing REVIEW exchange=%s rk=%s payload=%s",
            self.review_exchange_name, self.review_routing_key, payload,
        )
        await self._review_exchange.publish(msg, routing_key=self.review_routing_key)
        logger.debug("Publish REVIEW ok (submissionId=%s)", submissionId)

    # -------------------------
    # Publish: REPORT
    # -------------------------
    async def publish_submission_report(
        self,
        assignmentId: str,
        submissionId: str,
        studentId: str,
        deliveredAt: datetime,
    ) -> None:
        """
        Invia un messaggio anche allo scambio di REPORT,
        consumato dai tuoi consumer (queue: 'submissions.reports').
        """
        await self._ensure_ready()
        assert self._report_exchange is not None

        payload = self._build_submission_payload(assignmentId, submissionId, studentId, deliveredAt)
        body = json.dumps(payload).encode("utf-8")
        msg = Message(
            body=body,
            content_type="application/json",
            delivery_mode=DeliveryMode.NOT_PERSISTENT,
            headers={"eventType": "submission.reported"},
        )

        logger.debug(
            "Publishing REPORT exchange=%s rk=%s payload=%s",
            self.report_exchange_name, self.report_routing_key, payload,
        )
        await self._report_exchange.publish(msg, routing_key=self.report_routing_key)
        logger.debug("Publish REPORT ok (submissionId=%s)", submissionId)
